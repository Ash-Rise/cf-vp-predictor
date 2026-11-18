import unittest

from predictor_core import build_official_events, estimate_delta, modeled_vp_contribution, simulate


def contest_event(kind, cid, ts, rank, key=None):
    return {
        "type": kind, "cid": cid, "ts": ts, "rank": rank,
        "name": f"Contest {cid}",
        "key": key or f"{kind}:{cid}:{ts}",
    }


def proxies():
    # Two matching historical competitors with slight deviations: ± outcomes.
    return [
        {"oldRating": old, "newRating": old + delta, "rank": rank}
        for old, rank, delta in [
            (1400, 100, 40), (1401, 101, 43), (1402, 102, 42),
            (1399, 99, 39), (1403, 103, 41),
        ]
    ]


class CoreTests(unittest.TestCase):
    def test_proxy_details_match_delta_and_avoid_equal_cost_dict_comparison(self):
        # Same (cost, rating, rank) is legal; the original tuple sort could crash.
        source = proxies() + [dict(proxies()[0])]
        delta, used = estimate_delta(1400, 100, source)
        self.assertIsInstance(delta, int)
        self.assertEqual(len(used), 5)
        self.assertEqual(used[0]["Official Delta"], 40)

    def test_only_vp_change_is_attributed_to_vp(self):
        ts = 1710000000
        events = [
            contest_event("REAL", 100, ts, 100),
            contest_event("VP", 101, ts + 1000, 99),
            contest_event("REAL", 102, ts + 2000, 102),
        ]
        changes = {100: proxies(), 101: proxies(), 102: proxies()}
        full, missing1 = simulate(events, changes)
        baseline, missing2 = simulate(events, changes, include_vp=False)
        self.assertEqual(missing1, [])
        self.assertEqual(missing2, [])
        self.assertEqual(sum(row["type"] == "VP" for row in full), 1)
        self.assertEqual(sum(row["type"] == "VP" for row in baseline), 0)
        self.assertEqual(
            modeled_vp_contribution(full, baseline),
            full[-1]["rating"] - baseline[-1]["rating"],
        )

    def test_two_sessions_same_contest_can_be_excluded_separately(self):
        ts = 1710000000
        a = contest_event("VP", 101, ts, 100)
        b = contest_event("VP", 101, ts + 200, 101)
        result, _ = simulate([a, b], {101: proxies()}, frozenset({a["key"]}))
        self.assertTrue(result[1]["unrated"])
        self.assertFalse(result[2]["unrated"])
        self.assertEqual(result[1]["delta"], 0)

    def test_missing_contest_data_is_reported_not_silently_removed(self):
        event = contest_event("REAL", 102, 1710000000, 88)
        history, missing = simulate([event], {102: None})
        self.assertEqual(missing, [event["key"]])
        self.assertEqual([row["type"] for row in history], ["INIT"])
        self.assertNotIn("rating", {k: v for k, v in history[-1].items() if k == "estimated_final"})

    def test_missing_middle_round_stops_before_later_rounds(self):
        ts = 1710000000
        events = [
            contest_event("REAL", 10, ts, 100),
            contest_event("VP", 11, ts + 100, 75),
            contest_event("REAL", 12, ts + 200, 90),
        ]
        history, missing = simulate(events, {10: proxies(), 11: None, 12: proxies()})
        self.assertEqual(missing, [events[1]["key"]])
        self.assertEqual([row["cid"] for row in history[1:]], [10])

    def test_official_time_is_contest_start_not_rating_update(self):
        records = [{
            "contestId": 123, "rank": 42, "contestName": "Round 123",
            "newRating": 1200, "ratingUpdateTimeSeconds": 200000,
        }]
        events, official, missing = build_official_events(records, {123: 180000})
        self.assertEqual(events[0]["ts"], 180000)
        self.assertEqual(int(official[0]["date"].timestamp()), 200000)
        self.assertEqual(missing, 0)

    def test_missing_start_is_reported(self):
        records = [{
            "contestId": 123, "rank": 42, "contestName": "Round 123",
            "newRating": 1200, "ratingUpdateTimeSeconds": 200000,
        }]
        events, _, missing = build_official_events(records, {})
        self.assertEqual(events[0]["ts"], 200000)
        self.assertEqual(missing, 1)

    def test_start_time_order_determines_rating_sequence(self):
        events = [
            contest_event("VP", 500, 1710001000, 30),
            contest_event("REAL", 501, 1710000000, 100),
        ]
        events.sort(key=lambda e: e["ts"])
        self.assertEqual([e["type"] for e in events], ["REAL", "VP"])


if __name__ == "__main__":
    unittest.main()
