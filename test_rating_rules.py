import unittest

from rating_rules import NEWCOMER_BONUSES, parse_unrated_vp_ids, visible_rating


class RatingRulesTests(unittest.TestCase):
    def test_new_account_starts_displaying_zero(self):
        self.assertEqual(visible_rating(1400, 0, newcomer_mode=True), 0)

    def test_first_and_sixth_round_promotions(self):
        self.assertEqual(visible_rating(1420, 1, newcomer_mode=True), 520)
        self.assertEqual(visible_rating(1450, 6, newcomer_mode=True), 1450)
        self.assertEqual(visible_rating(1450, 10, newcomer_mode=True), 1450)
        self.assertEqual(sum(NEWCOMER_BONUSES), 1400)

    def test_internal_rating_stays_unchanged_for_regular_account(self):
        self.assertEqual(visible_rating(1643, 2, newcomer_mode=False), 1643)

    def test_explicit_unrated_ids(self):
        self.assertEqual(parse_unrated_vp_ids("123, 456，123"), frozenset({123, 456}))
        self.assertEqual(parse_unrated_vp_ids(" "), frozenset())

    def test_rejects_bad_unrated_ids(self):
        with self.assertRaises(ValueError):
            parse_unrated_vp_ids("123,not-a-contest")


if __name__ == "__main__":
    unittest.main()
