#!/usr/bin/env python3
"""Starts the game on this computer and shows the address players should open.

    python start.py            start (or restart) everything, copy the address, open the browser
    python start.py --stop     stop everything
    python start.py --ip 192.168.0.10     use this address instead of looking for one

It needs Docker and nothing else (standard library only). The address it finds is passed
to the game as PUBLIC_URL, so the board shows the right link and QR code.
"""
import argparse
import ipaddress
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Iterable, List, Optional

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8080


# ------------------------------------------------------------- finding the address
LAN_NETWORKS = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")]


def usable(ip: str) -> bool:
    """An address from the standard local-network ranges, which other devices could reach."""
    try:
        addr = ipaddress.IPv4Address(ip)
    except ValueError:
        return False
    return any(addr in network for network in LAN_NETWORKS)


def _score(ip: str, route_ip: Optional[str]) -> int:
    if ip.startswith("192.168.137.") or ip.startswith("10.42.0."):
        return 0   # a hotspot made by this computer (Windows / Linux): players will use it
    if ip == route_ip:
        return 1   # the address the computer uses to reach the network
    if ip.startswith("192.168.56.") or ip.startswith("192.168.99."):
        return 6   # VirtualBox / old Docker Toolbox
    if ip.startswith("192.168."):
        return 2
    if ip.startswith("10."):
        return 3
    return 5       # 172.16-31: usually Docker or Hyper-V, rarely the real network


def rank_addresses(candidates: Iterable[str], route_ip: Optional[str] = None) -> List[str]:
    """Usable addresses, most likely the right one first, without duplicates."""
    seen, ordered = set(), []
    for ip in candidates:
        if ip not in seen and usable(ip):
            seen.add(ip)
            ordered.append(ip)
    return sorted(ordered, key=lambda ip: _score(ip, route_ip))  # sorted() is stable


def route_address() -> Optional[str]:
    """The local address used to reach the network. Nothing is sent: connecting a UDP
    socket only makes the system pick the interface."""
    for probe in ("10.255.255.255", "192.168.255.255", "8.8.8.8"):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect((probe, 9))
            return sock.getsockname()[0]
        except OSError:
            continue
        finally:
            sock.close()
    return None


def candidate_addresses() -> List[str]:
    found = []
    route = route_address()
    if route:
        found.append(route)
    try:
        found += [info[4][0] for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)]
    except OSError:
        pass
    if shutil.which("hostname") and not sys.platform.startswith("win"):
        try:
            out = subprocess.run(["hostname", "-I"], capture_output=True, text=True, timeout=5).stdout
            found += out.split()
        except (OSError, subprocess.SubprocessError):
            pass
    return rank_addresses(found, route)


# ----------------------------------------------------------------- small helpers
def copy_to_clipboard(text: str) -> bool:
    if sys.platform.startswith("win"):
        commands = [["clip"]]
    elif sys.platform == "darwin":
        commands = [["pbcopy"]]
    else:
        commands = [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]
    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            subprocess.run(command, input=text.encode("utf-8"), check=True, timeout=5)
            return True
        except (OSError, subprocess.SubprocessError):
            continue
    return False


def wait_until_ready(url: str, timeout: float = 180, interval: float = 2, out=sys.stdout) -> bool:
    """Polls `url` until it answers 200 (the game takes a little while to start)."""
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        out.write(".")
        out.flush()
        time.sleep(interval)
    return False


def choose(addresses: List[str], interactive: bool) -> str:
    if len(addresses) == 1 or not interactive:
        return addresses[0]
    print("\nНайдено несколько сетевых адресов этого компьютера:")
    for number, ip in enumerate(addresses, start=1):
        print(f"  {number}. {ip}" + ("   <- вероятнее всего" if number == 1 else ""))
    answer = input("Номер адреса, по которому игроки будут заходить (Enter = 1): ").strip()
    if answer.isdigit() and 1 <= int(answer) <= len(addresses):
        return addresses[int(answer) - 1]
    return addresses[0]


def run_compose(args: List[str], env: dict) -> int:
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, env=env).returncode


def banner(url: str, copied: bool) -> str:
    line = "=" * (len(url) + 8)
    parts = ["", line, "  Игра запущена!", "", f"  Адрес для игроков:   {url}", line]
    if copied:
        parts.append("  Адрес скопирован в буфер обмена.")
    parts += [
        "  На табло (проектор) откройте этот же адрес и создайте игру:",
        "  на экране появятся QR-код и код комнаты.",
        "  Остановить игру:  python start.py --stop",
        "",
    ]
    return "\n".join(parts)


# ------------------------------------------------------------------------- main
def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Запуск игры и адрес для игроков")
    parser.add_argument("--ip", help="использовать этот адрес вместо автоматического поиска")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help=f"порт сайта (по умолчанию {DEFAULT_PORT})")
    parser.add_argument("--stop", action="store_true", help="остановить игру")
    parser.add_argument("--no-open", action="store_true", help="не открывать браузер")
    parser.add_argument("--no-copy", action="store_true", help="не копировать адрес в буфер обмена")
    args = parser.parse_args(argv)

    env = os.environ.copy()
    env["FRONTEND_PORT"] = str(args.port)

    if shutil.which("docker") is None or run_compose(["version"], env) != 0:
        print("Не найден Docker (или он не запущен). Установите Docker Desktop, запустите его и повторите.")
        return 1
    if args.stop:
        return run_compose(["down"], env)

    ip = args.ip
    if not ip:
        addresses = candidate_addresses()
        if addresses:
            ip = choose(addresses, interactive=sys.stdin.isatty())
        else:
            print("Не удалось найти адрес в локальной сети. Подключите компьютер к сети (или включите "
                  "точку доступа) и запустите снова, либо укажите адрес: python start.py --ip 192.168.0.10")
            ip = "localhost"
    url = f"http://{ip}:{args.port}"
    env["PUBLIC_URL"] = url

    print(f"Запускаю игру (адрес для игроков: {url}). Первый запуск может занять несколько минут...")
    if run_compose(["up", "-d", "--build"], env) != 0:
        print("Не удалось запустить. Подробности:  docker compose logs --tail 50")
        return 1

    sys.stdout.write("Жду, пока игра будет готова")
    if not wait_until_ready(f"http://127.0.0.1:{args.port}/api/health"):
        print("\nИгра не отвечает. Посмотрите:  docker compose logs --tail 50 backend")
        return 1
    print()

    copied = False if args.no_copy else copy_to_clipboard(url)
    print(banner(url, copied))
    if not args.no_open:
        webbrowser.open(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
