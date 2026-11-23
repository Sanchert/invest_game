import io
import sys
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import start  # noqa: E402  (the launcher in the project root)


class UsableTests(unittest.TestCase):
    def test_lan_addresses_are_usable(self):
        for ip in ("192.168.0.10", "10.0.0.5", "172.20.1.4", "192.168.137.1"):
            self.assertTrue(start.usable(ip), ip)

    def test_others_are_not(self):
        for ip in ("127.0.0.1", "169.254.10.2", "0.0.0.0", "8.8.8.8", "224.0.0.1", "192.0.2.2",
                   "100.64.1.1", "not-an-ip", "", "::1"):
            self.assertFalse(start.usable(ip), ip)


class RankTests(unittest.TestCase):
    def test_removes_duplicates_and_unusable(self):
        self.assertEqual(start.rank_addresses(["192.168.0.5", "127.0.0.1", "192.168.0.5", "8.8.8.8"]),
                         ["192.168.0.5"])

    def test_own_hotspot_comes_first(self):
        ips = ["10.1.2.3", "192.168.137.1", "192.168.0.7"]
        self.assertEqual(start.rank_addresses(ips, route_ip="10.1.2.3")[0], "192.168.137.1")

    def test_route_address_beats_other_lan_addresses(self):
        ips = ["192.168.0.7", "10.1.2.3", "172.18.0.1"]
        self.assertEqual(start.rank_addresses(ips, route_ip="10.1.2.3"), ["10.1.2.3", "192.168.0.7", "172.18.0.1"])

    def test_virtual_adapters_come_last(self):
        ips = ["172.17.0.1", "192.168.56.1", "10.0.0.8", "192.168.1.20"]
        self.assertEqual(start.rank_addresses(ips), ["192.168.1.20", "10.0.0.8", "172.17.0.1", "192.168.56.1"])

    def test_nothing_usable(self):
        self.assertEqual(start.rank_addresses(["127.0.0.1"]), [])


class ChooseTests(unittest.TestCase):
    def test_single_or_non_interactive_takes_the_first(self):
        self.assertEqual(start.choose(["10.0.0.1", "192.168.0.2"], interactive=False), "10.0.0.1")
        self.assertEqual(start.choose(["10.0.0.1"], interactive=True), "10.0.0.1")


class BannerTests(unittest.TestCase):
    def test_contains_the_address_and_clipboard_note(self):
        text = start.banner("http://192.168.0.10:8080", copied=True)
        self.assertIn("http://192.168.0.10:8080", text)
        self.assertIn("буфер", text)
        self.assertNotIn("буфер", start.banner("http://x:1", copied=False))


class _Health(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass


class WaitTests(unittest.TestCase):
    def test_returns_true_when_the_server_answers(self):
        server = HTTPServer(("127.0.0.1", 0), _Health)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/health"
            self.assertTrue(start.wait_until_ready(url, timeout=5, interval=0.1, out=io.StringIO()))
        finally:
            server.shutdown()

    def test_returns_false_on_timeout(self):
        self.assertFalse(start.wait_until_ready("http://127.0.0.1:9/none", timeout=0.5, interval=0.1,
                                                out=io.StringIO()))


if __name__ == "__main__":
    unittest.main()
