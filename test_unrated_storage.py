import unittest

from unrated_storage import parse_saved_value


class UnratedBrowserSettingsTests(unittest.TestCase):
    def test_restores_only_valid_sessions_for_current_handle(self):
        raw = '{"handle":"alice","keys":["VP:11:100","VP:12:200","VP:99:999"]}'
        self.assertEqual(parse_saved_value(raw, "alice", {"VP:11:100", "VP:12:200"}), {"VP:11:100", "VP:12:200"})

    def test_ignores_other_handles_and_broken_storage(self):
        self.assertIsNone(parse_saved_value('{"handle":"alice","keys":["VP:1:2"]}', "bob", {"VP:1:2"}))
        self.assertIsNone(parse_saved_value("not-json", "alice", {"VP:1:2"}))
        self.assertIsNone(parse_saved_value("", "alice", {"VP:1:2"}))
        self.assertEqual(parse_saved_value('{"handle":"alice","keys":[]}', "alice", {"VP:1:2"}), set())


if __name__ == "__main__":
    unittest.main()
