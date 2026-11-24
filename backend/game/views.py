"""What the screens are shown: the public board and a team's private view."""
from sqlalchemy import select
from sqlalchemy.orm import Session

import rules
import settings
from constants import Phase
from game.common import insider_candidates, iso, load_startups, rule_info
from models import (Game, Holding, Insider, News, Snapshot, Startup, Team, TeamInsider, TurnGain,
                    utcnow)
from schemas import (BoardOut, BoardStartup, BoardTeam, Chart, ChartSeries, HoldingOut,
                     InsiderOut, MeOut, TurnGainOut)
from game.common import list_teams


def build_me(db: Session, game: Game, team: Team) -> MeOut:
    info = load_startups(db, game.id)
    rows = db.execute(select(Holding).where(Holding.team_id == team.id)
                      .order_by(Holding.startup_id)).scalars().all()
    # Shares are worth this turn's price while it is running, and the newly revealed
    # price once the turn has been resolved.
    if game.phase == Phase.TURN:
        step = game.turn_no
    elif game.phase in (Phase.RESULTS, Phase.FINISHED):
        step = game.turn_no + 1
    else:
        step = 1
    holdings = {h.startup_id: h.shares for h in rows}
    shares_value = rules.holdings_value(holdings, rule_info(info), step) if holdings else 0

    tips = db.execute(
        select(Insider, Startup)
        .join(TeamInsider, TeamInsider.insider_id == Insider.id)
        .join(Startup, Startup.id == Insider.startup_id)
        .where(TeamInsider.team_id == team.id)
        .order_by(Insider.turn, Insider.id)
    ).all()
    left = len(insider_candidates(db, game, team.id)) if game.phase == Phase.TURN else 0

    rank = score = turn_gain = None
    gains = []
    if game.phase in (Phase.RESULTS, Phase.FINISHED):
        gains = [TurnGainOut(startup_id=g.startup_id, shares=g.shares, gain=g.gain)
                 for g in db.execute(select(TurnGain).where(
                     TurnGain.team_id == team.id, TurnGain.turn_no == game.turn_no)
                     .order_by(TurnGain.startup_id)).scalars()]
        turn_gain = sum(g.gain for g in gains)
        snap = db.get(Snapshot, (team.id, game.turn_no))
        if snap:
            rank = snap.rank
            if game.phase == Phase.FINISHED:
                score = snap.score
    return MeOut(
        team_id=team.id, name=team.name, ready=team.ready, cash=team.cash,
        capital=team.cash + shares_value,
        holdings=[HoldingOut(startup_id=h.startup_id, shares=h.shares) for h in rows],
        insiders=[InsiderOut(turn=i.turn, startup_id=s.id, startup_name=s.name, text=i.text)
                  for i, s in tips],
        insider_cost=rules.insider_cost(max(game.turn_no, 1), settings.INSIDER_COSTS),
        insiders_left=left, rank=rank, score=score, turn_gains=gains, turn_gain=turn_gain,
    )


def build_board(db: Session, game: Game) -> BoardOut:
    teams = list_teams(db, game.id)
    info = load_startups(db, game.id)
    phase = Phase(game.phase)
    show_ranks = phase in (Phase.RESULTS, Phase.FINISHED)

    snaps = {}
    if show_ranks and teams:
        for s in db.execute(select(Snapshot).where(
                Snapshot.team_id.in_([x.id for x in teams]),
                Snapshot.turn_no == game.turn_no)).scalars():
            snaps[s.team_id] = s

    news_by_startup: dict = {}
    if phase == Phase.TURN and game.turn_no >= 2 and info:
        for n in db.execute(select(News).where(
                News.turn == game.turn_no, News.startup_id.in_(list(info)))
                .order_by(News.id)).scalars():
            news_by_startup.setdefault(n.startup_id, []).append(n.text)

    startups = []
    for sid, entry in info.items():
        last, prices, turn = entry["last_turn"], entry["prices"], game.turn_no
        if phase in (Phase.LOBBY, Phase.TURN):
            step = max(turn, 1)
            is_open = step <= last
            price, prev = (prices.get(step) if is_open else None), None
        else:  # RESULTS / FINISHED: show the price that was just revealed
            is_open = phase == Phase.RESULTS and turn + 1 <= last
            price = prices.get(turn + 1) if turn <= last else None
            prev = prices.get(turn) if turn <= last else None
        startups.append(BoardStartup(
            id=sid, name=entry["startup"].name, description=entry["startup"].description,
            open=is_open, last_turn=last, price=price, prev_price=prev,
            news="\n".join(news_by_startup[sid]) if sid in news_by_startup else None,
        ))

    chart = None
    if phase == Phase.FINISHED and teams:
        by_team: dict = {x.id: {} for x in teams}
        for s in db.execute(select(Snapshot).where(
                Snapshot.team_id.in_(list(by_team)))).scalars():
            by_team[s.team_id][s.turn_no] = s.score
        order = sorted(teams, key=lambda x: snaps[x.id].rank if x.id in snaps else 99)
        turns = list(range(0, game.turns_total + 1))
        chart = Chart(turns=turns, series=[
            ChartSeries(team=x.name, scores=[by_team[x.id].get(n, 0) for n in turns])
            for x in order])

    return BoardOut(
        room_code=game.room_code, phase=phase, turn_no=game.turn_no,
        turns_total=game.turns_total, turn_seconds=game.turn_seconds,
        min_teams=settings.MIN_TEAMS, server_time=iso(utcnow()),
        phase_ends_at=iso(game.phase_ends_at), countdown_ends_at=iso(game.countdown_ends_at),
        teams=[BoardTeam(
            id=x.id, name=x.name, ready=x.ready,
            rank=snaps[x.id].rank if x.id in snaps else None,
            score=snaps[x.id].score if (phase == Phase.FINISHED and x.id in snaps) else None,
        ) for x in teams],
        startups=startups, chart=chart,
    )
