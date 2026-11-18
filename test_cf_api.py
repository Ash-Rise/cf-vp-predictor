import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cf_api


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.patcher = patch.object(cf_api, "CACHE_DIR", Path(self.tempdir.name))
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tempdir.cleanup()

    def test_rating_changes_are_cached_and_shared(self):
        rows = [{"rank": 1, "oldRating": 1400, "newRating": 1450}]
        with patch.object(cf_api, "_remote", return_value=rows) as remote:
            self.assertEqual(
                cf_api.get_json("contest.ratingChanges", {"contestId": 42}),
                rows,
            )
            self.assertEqual(
                cf_api.get_json("contest.ratingChanges", {"contestId": 42}),
                rows,
            )
            self.assertEqual(remote.call_count, 1)

    def test_incremental_user_status_refreshes_recent_pending_verdicts(self):
        initial = [
            {"id": 20, "verdict": "TESTING"},
            {"id": 19, "verdict": "OK"},
        ]
        updated = [
            {"id": 22, "verdict": "OK"},
            {"id": 21, "verdict": "WRONG_ANSWER"},
            {"id": 20, "verdict": "OK"},
        ]
        with patch.object(cf_api, "_remote", side_effect=[initial, updated]) as remote:
            first = cf_api.get_user_submissions("TestHandle")
            self.assertEqual([row["id"] for row in first], [20, 19])
            path = cf_api._personal_path("TestHandle")
            state = cf_api._read(path)
            state["fetched"] = 0
            cf_api._write(path, state)
            result = cf_api.get_user_submissions("TestHandle")
            self.assertEqual([row["id"] for row in result], [22, 21, 20, 19])
            self.assertEqual(result[2]["verdict"], "OK")
            self.assertEqual(remote.call_count, 2)
            self.assertEqual(remote.call_args.args[0], "user.status")
            self.assertEqual(remote.call_args.args[1]["count"], 200)

    def test_clear_personal_cache_keeps_shared_contest_cache(self):
        with patch.object(cf_api, "_remote", return_value=[
            {"rank": 1, "oldRating": 1400, "newRating": 1450}
        ]):
            cf_api.get_json("contest.ratingChanges", {"contestId": 42})
        cf_api._write(cf_api._personal_path("someone"), {
            "fetched": 20, "submissions": []
        })
        cf_api.clear_personal_cache("someone")
        self.assertFalse(cf_api._personal_path("someone").exists())
        self.assertIsNotNone(cf_api._read(
            cf_api._path("contest.ratingChanges", {"contestId": 42})
        ))


if __name__ == "__main__":
    unittest.main()
