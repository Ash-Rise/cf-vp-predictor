"""Startup smoke test: exercise the Streamlit entrypoint, not just helper imports.

The custom handle component's browser JS cannot run in AppTest; only that
browser-facing input is stubbed. All other app modules import normally.
"""

import sys
import types
import unittest
from unittest.mock import patch


class StartupTests(unittest.TestCase):
    def test_app_startup_vp_manager_and_prediction_details(self):
        from datetime import datetime, timezone
        from streamlit.testing.v1 import AppTest

        fake = types.ModuleType("persistent_handle")
        fake.persistent_handle_input = lambda label: "Tester"
        since = 1710000000
        events = [
            {
                "key": "REAL:10:1710000100", "cid": 10, "ts": since,
                "type": "REAL", "rank": 10, "name": "Official Round",
            },
            {
                "key": "VP:11:1710001000", "cid": 11, "ts": since + 1000,
                "type": "VP", "rank": 12, "name": "Virtual Round",
                "vp_details": {
                    "rank": 12, "score": 250.0, "solved": 1,
                    "penalty": None, "scoring": "CF",
                    "problems": [{"problem": "A", "minute": 50, "wrong_attempts": 1}],
                },
            },
        ]
        sample = [
            {"rank": rank, "oldRating": 1400 + rank,
             "newRating": 1440 + rank}
            for rank in (9, 10, 11, 12, 13)
        ]
        fake_data = {
            "handle": "Tester", "events": events,
            "changes": {10: sample, 11: sample}, "warnings": [],
            "real_history": [{
                "date": datetime.fromtimestamp(since + 2000, timezone.utc),
                "rating": 1450, "name": "Official Round", "rank": 10,
            }],
        }

        with patch.dict(sys.modules, {"persistent_handle": fake}):
            app = AppTest.from_file("app.py", default_timeout=25)
            app.session_state["analysis_data"] = fake_data
            app.run()
        self.assertFalse(
            app.exception,
            "\n".join(str(item.message) for item in app.exception),
        )
        self.assertTrue(app.data_editor)
        self.assertTrue(app.selectbox)
        # No redundant contest-ID input: Unrated is managed in the table.
        self.assertEqual(len(app.text_input), 0)


if __name__ == "__main__":
    unittest.main()
