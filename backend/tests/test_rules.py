import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rules  # noqa: E402
import settings  # noqa: E402

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

# Prices from the Excel model the game was played with (columns Морфеус..Афина).
EXCEL = {
    1: {"last_turn": 3, "prices": {1: 10, 2: 41, 3: 86, 4: 9}},    # Морфеус
    2: {"last_turn": 3, "prices": {1: 10, 2: 45, 3: 38, 4: 15}},   # Миллениум
    3: {"last_turn": 3, "prices": {1: 10, 2: 25, 3: 30, 4: 0}},    # Блейдворк
    4: {"last_turn": 3, "prices": {1: 10, 2: 25, 3: 30, 4: 50}},   # Фотосток
    5: {"last_turn": 3, "prices": {1: 10, 2: 25, 3: 30, 4: 50}},   # Афина
}


class RankTests(unittest.TestCase):
    def test_competition_ranking(self):
        r = rules.rank_scores({"a": 50, "b": 80, "c": 80, "d": 10})
        self.assertEqual(r, {"b": 1, "c": 1, "a": 3, "d": 4})

    def test_empty(self):
        self.assertEqual(rules.rank_scores({}), {})


class ExcelGameTests(unittest.TestCase):
    """Replays a whole game with the Excel formulas and checks the same totals."""

    def test_buy_hold_and_sell_scenario(self):
        cash = 600
        # Turn 1: buy 20 Морфеус at 10.
        cash -= 20 * rules.trading_price(EXCEL[1], 1)
        holdings = {1: 20}
        cash, holdings, value = rules.resolve_turn(cash, holdings, 1, EXCEL)
        self.assertEqual((cash, holdings, value), (400, {1: 20}, 20 * 41))
        # Turn 2: sell 10 at 41.
        cash += 10 * rules.trading_price(EXCEL[1], 2)
        holdings = {1: 10}
        cash, holdings, value = rules.resolve_turn(cash, holdings, 2, EXCEL)
        self.assertEqual((cash, holdings, value), (810, {1: 10}, 10 * 86))
        # Turn 3 (last): nothing traded; Морфеус ends at 9.
        cash, holdings, value = rules.resolve_turn(cash, holdings, 3, EXCEL)
        self.assertEqual((cash, holdings, value), (810 + 10 * 9, {}, 0))
        self.assertEqual(cash - 600, 300)

    def test_capital_can_fall(self):
        # 60 shares of Блейдворк bought at 10 end worthless.
        cash, holdings = 0, {3: 60}
        for turn in (1, 2, 3):
            cash, holdings, value = rules.resolve_turn(cash, holdings, turn, EXCEL)
        self.assertEqual(cash + value, 0)

    def test_trading_price_and_closing(self):
        self.assertEqual(rules.trading_price(EXCEL[1], 2), 41)
        self.assertEqual(rules.trading_price(EXCEL[1], 3), 86)
        self.assertIsNone(rules.trading_price(EXCEL[1], 4))

    def test_shares_are_valued_at_the_new_price(self):
        _, _, value = rules.resolve_turn(0, {1: 5, 2: 2}, 1, EXCEL)
        self.assertEqual(value, 5 * 41 + 2 * 45)

    def test_startup_that_closes_early_is_cashed_out(self):
        startups = {1: {"last_turn": 1, "prices": {1: 10, 2: 14}},
                    2: {"last_turn": 3, "prices": {1: 10, 2: 11, 3: 12, 4: 13}}}
        cash, holdings, value = rules.resolve_turn(0, {1: 4, 2: 3}, 1, startups)
        self.assertEqual(cash, 4 * 14)
        self.assertEqual(holdings, {2: 3})
        self.assertEqual(value, 3 * 11)

    def test_zero_shares_ignored(self):
        self.assertEqual(rules.resolve_turn(7, {1: 0}, 1, EXCEL), (7, {}, 0))

    def test_holdings_value_falls_back_to_final_price(self):
        startups = {1: {"last_turn": 1, "prices": {1: 10, 2: 14}}}
        self.assertEqual(rules.holdings_value({1: 2}, startups, 5), 28)


class TurnGainTests(unittest.TestCase):
    def test_gain_is_shares_times_price_change(self):
        gains = rules.turn_gains({1: 12, 3: 8}, 2, EXCEL)
        self.assertEqual(gains, {1: (12, 12 * (86 - 41)), 3: (8, 8 * (30 - 25))})

    def test_loss_is_negative(self):
        self.assertEqual(rules.turn_gains({1: 10}, 3, EXCEL), {1: (10, 10 * (9 - 86))})

    def test_startup_that_went_to_zero(self):
        self.assertEqual(rules.turn_gains({3: 60}, 3, EXCEL), {3: (60, -1800)})

    def test_zero_shares_and_missing_prices_are_skipped(self):
        self.assertEqual(rules.turn_gains({1: 0}, 1, EXCEL), {})
        self.assertEqual(rules.turn_gains({1: 5}, 4, EXCEL), {})

    def test_gains_add_up_to_the_change_in_capital(self):
        cash, holdings = 100, {1: 7, 2: 3}
        before = cash + 7 * 41 + 3 * 45
        gains = rules.turn_gains(holdings, 2, EXCEL)
        cash, holdings, value = rules.resolve_turn(cash, holdings, 2, EXCEL)
        self.assertEqual(cash + value - before, sum(g for _, g in gains.values()))


class InsiderCostTests(unittest.TestCase):
    def test_excel_prices_per_turn(self):
        self.assertEqual([rules.insider_cost(t, settings.INSIDER_COSTS) for t in (1, 2, 3)],
                         [5, 10, 30])

    def test_last_price_repeats(self):
        self.assertEqual(rules.insider_cost(7, (5, 10, 30)), 30)
        self.assertEqual(rules.insider_cost(0, (5, 10, 30)), 5)


class EffectiveTurnsTests(unittest.TestCase):
    def test_capped_by_longest_startup(self):
        self.assertEqual(rules.effective_turns(10, [3, 5, 4]), 5)

    def test_requested_is_smaller(self):
        self.assertEqual(rules.effective_turns(2, [3, 5]), 2)

    def test_no_startups(self):
        with self.assertRaises(ValueError):
            rules.effective_turns(3, [])


class LobbyTests(unittest.TestCase):
    def test_needs_min_teams(self):
        self.assertEqual(rules.lobby_action(1, True, 2, None, NOW), "idle")

    def test_all_ready_begins_countdown(self):
        self.assertEqual(rules.lobby_action(2, True, 2, None, NOW), "begin_countdown")

    def test_countdown_running(self):
        end = NOW + timedelta(seconds=5)
        self.assertEqual(rules.lobby_action(2, True, 2, end, NOW), "idle")

    def test_countdown_finished_starts(self):
        end = NOW - timedelta(seconds=1)
        self.assertEqual(rules.lobby_action(3, True, 2, end, NOW), "start")

    def test_unready_or_new_team_cancels(self):
        end = NOW + timedelta(seconds=5)
        self.assertEqual(rules.lobby_action(3, False, 2, end, NOW), "cancel_countdown")
        self.assertEqual(rules.lobby_action(3, False, 2, None, NOW), "idle")


class RoomCodeTests(unittest.TestCase):
    def test_alphabet_and_length(self):
        code = rules.make_room_code(random.Random(1))
        self.assertEqual(len(code), rules.ROOM_CODE_LENGTH)
        self.assertTrue(set(code) <= set(rules.ROOM_ALPHABET))
        self.assertFalse(set("0O1IL") & set(rules.ROOM_ALPHABET))


def good_pack():
    return {"startups": [{
        "slug": "demo", "name": "Demo", "description": "A demo startup.",
        "prices": [10, 25, 0],
        "news": [{"turn": 2, "text": "Good news."}],
        "insiders": [{"turn": 1, "text": "Early tip."}, {"turn": 2, "text": "A tip."}],
    }]}


class PackTests(unittest.TestCase):
    def test_valid_pack(self):
        out = rules.validate_pack(good_pack())
        self.assertEqual(out[0]["prices"], [10, 25, 0])
        self.assertEqual(len(out[0]["insiders"]), 2)

    def _expect_error(self, mutate, fragment):
        pack = good_pack()
        mutate(pack["startups"][0])
        with self.assertRaises(ValueError) as ctx:
            rules.validate_pack(pack)
        self.assertIn(fragment, str(ctx.exception))

    def test_errors(self):
        self._expect_error(lambda s: s.update(slug="Bad Slug"), "slug")
        self._expect_error(lambda s: s.update(prices=[10]), "at least 2")
        self._expect_error(lambda s: s.update(prices=[10, -1, 5]), "price 2")
        self._expect_error(lambda s: s.update(prices=[10, 2.5, 5]), "price 2")
        self._expect_error(lambda s: s.update(prices=[0, 5, 5]), "first price")
        self._expect_error(lambda s: s["news"][0].update(turn=1), "between 2 and 2")
        self._expect_error(lambda s: s["insiders"][0].update(turn=3), "between 1 and 2")
        self._expect_error(lambda s: s.update(name=" "), "name")
        self._expect_error(lambda s: s["insiders"][0].update(text=""), "text")

    def test_bad_shape(self):
        for bad in (None, [], {"startups": []}, {"startups": "x"}):
            with self.assertRaises(ValueError):
                rules.validate_pack(bad)

    def test_duplicate_slug(self):
        pack = good_pack()
        pack["startups"].append(dict(pack["startups"][0]))
        with self.assertRaises(ValueError):
            rules.validate_pack(pack)


if __name__ == "__main__":
    unittest.main()
