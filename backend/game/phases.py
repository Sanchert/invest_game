"""The phase machine: LOBBY -> TURN -> RESULTS -> TURN -> ... -> FINISHED.

Locking order is always: game row, then team rows. The timer loop and the player
endpoints both follow it, so they cannot deadlock, and every transition is decided
while holding the game row lock, so it can only happen once."""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

import rules
import settings
from constants import Phase
from game.common import aware, list_teams, load_startups, rule_info
from models import Game, Holding, Snapshot, TurnGain, utcnow
from presence import presence


def tick(db: Session, game_id: int) -> None:
    """Advance a game if (and only if) something is due. Safe to call at any time,
    from any thread, as often as you like."""
    game = db.execute(
        select(Game).where(Game.id == game_id).with_for_update()
    ).scalar_one_or_none()
    if game is None or game.phase == Phase.FINISHED:
        db.rollback()
        return
    now = utcnow()
    if game.phase == Phase.LOBBY:
        _tick_lobby(db, game, now)
    elif game.phase == Phase.TURN:
        ends = aware(game.phase_ends_at)
        due = ends is not None and now >= ends
        teams = list_teams(db, game.id)
        if due or (teams and all(x.ready for x in teams)):
            _end_turn(db, game, now)
    elif game.phase == Phase.RESULTS:
        ends = aware(game.phase_ends_at)
        if ends is not None and now >= ends:
            _begin_turn(db, game, game.turn_no + 1, now)
    db.commit()


def _tick_lobby(db: Session, game: Game, now: datetime) -> None:
    teams = list_teams(db, game.id, lock=True)
    alive = []
    for team in teams:
        if presence.idle_seconds(team.id) > settings.STALE_LOBBY_SECONDS:
            presence.forget(team.id)
            db.delete(team)
        else:
            alive.append(team)
    action = rules.lobby_action(
        len(alive),
        bool(alive) and all(x.ready for x in alive),
        settings.MIN_TEAMS,
        aware(game.countdown_ends_at),
        now,
    )
    if action == "begin_countdown":
        game.countdown_ends_at = now + timedelta(seconds=settings.COUNTDOWN_SECONDS)
    elif action == "cancel_countdown":
        game.countdown_ends_at = None
    elif action == "start":
        game.countdown_ends_at = None
        _begin_turn(db, game, 1, now, alive)


def _begin_turn(db: Session, game: Game, turn_no: int, now: datetime,
                teams: Optional[list] = None) -> None:
    teams = teams if teams is not None else list_teams(db, game.id, lock=True)
    game.phase = Phase.TURN.value
    game.turn_no = turn_no
    game.phase_ends_at = now + timedelta(seconds=game.turn_seconds)
    game.phase_changed_at = now
    for team in teams:
        team.ready = False
        if turn_no == 1:  # the starting point of the final chart
            db.add(Snapshot(team_id=team.id, turn_no=0, cash=team.cash,
                            shares_value=0, score=0, rank=1))


def _end_turn(db: Session, game: Game, now: datetime) -> None:
    teams = list_teams(db, game.id, lock=True)
    holdings_by_team: dict = {}
    if teams:
        for h in db.execute(
            select(Holding).where(Holding.team_id.in_([x.id for x in teams]))
        ).scalars():
            holdings_by_team.setdefault(h.team_id, []).append(h)
    startups = rule_info(load_startups(db, game.id))

    scores, parts = {}, {}
    for team in teams:
        rows = holdings_by_team.get(team.id, [])
        held = {h.startup_id: h.shares for h in rows}
        for sid, (shares, gain) in rules.turn_gains(held, game.turn_no, startups).items():
            db.add(TurnGain(team_id=team.id, turn_no=game.turn_no, startup_id=sid,
                            shares=shares, gain=gain))
        cash, new_holdings, value = rules.resolve_turn(team.cash, held, game.turn_no, startups)
        team.cash = cash
        team.ready = True  # a team that never pressed Ready is confirmed automatically
        for h in rows:
            if h.startup_id in new_holdings:
                h.shares = new_holdings[h.startup_id]
            else:
                db.delete(h)
        scores[team.id] = cash + value - settings.STARTING_CAPITAL
        parts[team.id] = (cash, value)

    ranks = rules.rank_scores(scores)
    for team in teams:
        cash, value = parts[team.id]
        db.add(Snapshot(team_id=team.id, turn_no=game.turn_no, cash=cash,
                        shares_value=value, score=scores[team.id], rank=ranks[team.id]))

    game.phase_changed_at = now
    if game.turn_no >= game.turns_total:
        game.phase = Phase.FINISHED.value
        game.phase_ends_at = None
    else:
        game.phase = Phase.RESULTS.value
        game.phase_ends_at = now + timedelta(seconds=settings.RESULTS_SECONDS)
