import unittest

from backtest import evaluate_contest, summarize


class BacktestTests(unittest.TestCase):
    def test_leave_one_out_excludes_target(self):
        changes = [
            {"handle": f"p{i}", "rank": i + 1, "oldRating": 1500 + i,
             "newRating": 1510 + i + 2 * i}
            for i in range(20)
        ]
        rows = evaluate_contest(changes, sample_size=5)
        self.assertEqual(len(rows), 5)
        for row in rows:
            self.assertEqual(row["prediction"] - row["actual"], row["error"])

    def test_metrics_are_absolute_and_signed(self):
        data = [{"error": -10}, {"error": -5}, {"error": 10}, {"error": 5}]
        report = summarize(data)
        self.assertEqual(report["mae"], 7.5)
        self.assertEqual(report["bias"], 0)
        self.assertEqual(report["p90_abs_error"], 10)

    def test_empty_result_explicit(self):
        self.assertEqual(summarize([])["sample_size"], 0)


if __name__ == "__main__":
    unittest.main()
