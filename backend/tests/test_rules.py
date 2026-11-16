import random
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import rules  # noqa: E402

NOW = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)


def startups():
    return {
        1: {"last_turn": 3, "turns": {1: (10, 2), 2: (10, 4), 3: (10, 7)}},
        2: {"last_turn": 2, "turns": {1: (10, 3), 2: (10, 0)}},
    }


class RankTests(unittest.TestCase):
    def test_competition_ranking(self):
        r = rules.rank_scores({"a": 50, "b": 80, "c": 80, "d": 10})
        self.assertEqual(r, {"b": 1, "c": 1, "a": 3, "d": 4})

    def test_empty(self):
        self.assertEqual(rules.rank_scores({}), {})


class ResolveTurnTests(unittest.TestCase):
    def test_profit_is_paid_to_cash(self):
        cash, holdings, value = rules.resolve_turn(100, {1: 5, 2: 2}, 1, startups())
        self.assertEqual(cash, 100 + 5 * 2 + 2 * 3)
        self.assertEqual(holdings, {1: 5, 2: 2})
        self.assertEqual(value, 70)

    def test_closed_startup_is_redeemed_at_buy_price(self):
        cash, holdings, value = rules.resolve_turn(0, {1: 5, 2: 2}, 2, startups())
        # startup 1 pays 4/share, startup 2 pays 0 and closes: 2 shares * 10 back
        self.assertEqual(cash, 5 * 4 + 2 * 0 + 2 * 10)
        self.assertEqual(holdings, {1: 5})
        self.assertEqual(value, 50)

    def test_zero_shares_ignored(self):
        cash, holdings, _ = rules.resolve_turn(7, {1: 0}, 1, startups())
        self.assertEqual((cash, holdings), (7, {}))

    def test_capital_never_drops_at_constant_price(self):
        cash, holdings = 600, {1: 30, 2: 30}
        capital_before = cash + rules.holdings_value(holdings, {1: 10, 2: 10})
        for turn in (1, 2, 3):
            cash, holdings, value = rules.resolve_turn(cash, holdings, turn, startups())
            self.assertGreaterEqual(cash + value, capital_before)
            capital_before = cash + value


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
        "turns": [{"turn": 1, "profit": 1}, {"turn": 2, "profit": 3, "buy_price": 12}],
        "news": [{"turn": 2, "text": "Good news."}],
        "insiders": [{"turn": 2, "text": "A tip."}],
    }]}


class PackTests(unittest.TestCase):
    def test_valid_pack_defaults_price(self):
        out = rules.validate_pack(good_pack())
        self.assertEqual(out[0]["turns"][0]["buy_price"], 10)
        self.assertEqual(out[0]["turns"][1]["buy_price"], 12)

    def _expect_error(self, mutate, fragment):
        pack = good_pack()
        mutate(pack["startups"][0])
        with self.assertRaises(ValueError) as ctx:
            rules.validate_pack(pack)
        self.assertIn(fragment, str(ctx.exception))

    def test_errors(self):
        self._expect_error(lambda s: s.update(slug="Bad Slug"), "slug")
        self._expect_error(lambda s: s["turns"][0].update(profit=-1), "profit")
        self._expect_error(lambda s: s["turns"][0].update(profit=1.5), "profit")
        self._expect_error(lambda s: s["turns"][1].update(turn=3), "numbered")
        self._expect_error(lambda s: s["news"][0].update(turn=1), "between 2 and 2")
        self._expect_error(lambda s: s["insiders"][0].update(turn=3), "between 2 and 2")
        self._expect_error(lambda s: s.update(name=" "), "name")
        self._expect_error(lambda s: s["turns"][1].update(buy_price=0), "buy_price")

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
