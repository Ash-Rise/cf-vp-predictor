import unittest

from datetime import datetime, timezone
from rating_rules import (
    NEWCOMER_BONUSES, DEFAULT_INITIAL_RATING, INTERNAL_START,
    display_simulation_rating, is_rated_simulation_event,
    simulation_start_rating, use_new_account_policy, visible_rating,
)


class RatingRulesTests(unittest.TestCase):
    def test_fixed_initial_rating_for_both_modes(self):
        self.assertEqual(DEFAULT_INITIAL_RATING, 100)
        self.assertEqual(INTERNAL_START, 1400)

    def test_new_account_starts_displaying_zero(self):
        self.assertEqual(visible_rating(1400, 0, newcomer_mode=True), 0)

    def test_first_and_sixth_round_promotions(self):
        self.assertEqual(visible_rating(1420, 1, newcomer_mode=True), 520)
        self.assertEqual(visible_rating(1450, 6, newcomer_mode=True), 1450)
        self.assertEqual(visible_rating(1450, 10, newcomer_mode=True), 1450)
        self.assertEqual(sum(NEWCOMER_BONUSES), 1400)

    def test_internal_rating_stays_unchanged_for_regular_account(self):
        self.assertEqual(visible_rating(1643, 2, newcomer_mode=False), 1643)

    def test_display_starts_at_zero_and_bonuses_apply_automatically(self):
        internal = INTERNAL_START
        self.assertEqual(display_simulation_rating(internal, 0, True), 0)
        ratings = []
        for i, estimated_delta in enumerate([20, -10, 30, 0, 5, -20, 15], 1):
            internal += estimated_delta
            ratings.append(display_simulation_rating(internal, i, True))
        self.assertEqual(ratings, [520, 860, 1140, 1290, 1395, 1425, 1440])

    def test_manual_unrated_does_not_consume_beginner_bonus(self):
        modern = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
        events = [
            {"type": "VP", "cid": 11, "ts": modern},
            {"type": "REAL", "cid": 12, "ts": modern + 100},
            {"type": "VP", "cid": 13, "ts": modern + 200},
        ]
        excluded = frozenset({11, 13})
        self.assertTrue(use_new_account_policy(events, excluded))
        self.assertEqual(simulation_start_rating(events, excluded), 1400)
        self.assertFalse(is_rated_simulation_event(events[0], excluded))
        self.assertTrue(is_rated_simulation_event(events[1], excluded))
        self.assertFalse(is_rated_simulation_event(events[2], excluded))
        # After only one eligible rated contest, the first 500-point bonus applies.
        self.assertEqual(display_simulation_rating(1420, 1, True), 520)

    def test_legacy_first_rated_date_skips_modern_bonus(self):
        old = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp())
        events = [{"type": "REAL", "cid": 100, "ts": old}]
        self.assertFalse(use_new_account_policy(events))
        self.assertEqual(simulation_start_rating(events), DEFAULT_INITIAL_RATING)
        self.assertEqual(display_simulation_rating(100, 0, False), 0)
        self.assertEqual(display_simulation_rating(115, 1, False), 115)

    def test_excluded_old_vp_does_not_force_legacy_policy(self):
        old = int(datetime(2019, 1, 1, tzinfo=timezone.utc).timestamp())
        modern = int(datetime(2024, 1, 1, tzinfo=timezone.utc).timestamp())
        events = [{"type": "VP", "cid": 100, "ts": old}, {"type": "REAL", "cid": 200, "ts": modern}]
        self.assertFalse(use_new_account_policy(events))
        self.assertTrue(use_new_account_policy(events, frozenset({100})))


if __name__ == "__main__":
    unittest.main()
