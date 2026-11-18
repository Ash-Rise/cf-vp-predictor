import unittest
from vp_utils import estimate_vp_rank, group_vp_sessions


def sub(cid, start, at, pid, verdict, kind='VIRTUAL'):
    return {'contestId': cid, 'creationTimeSeconds': at,
            'author': {'participantType': kind, 'startTimeSeconds': start},
            'problem': {'index': pid}, 'verdict': verdict}


class VPTests(unittest.TestCase):
    def test_group_sessions_uses_start_times(self):
        submissions = [sub(100, 1000, 1020, 'A', 'OK'),
                       sub(100, 10000, 10020, 'A', 'WRONG_ANSWER'),
                       sub(100, 10000, 10080, 'A', 'OK'),
                       sub(100, 1000, 1040, 'B', 'OK')]
        runs = group_vp_sessions(submissions)
        self.assertEqual([(c, t, len(v)) for c, t, v in runs],
                         [(100, 1000, 2), (100, 10000, 2)])

    def test_cf_time_and_failed_attempts(self):
        # 150-min round: P=1000, t=50, WA=2 => 740 (floor(160)+100).
        standings = {'contest': {'type': 'CF', 'durationSeconds': 9000},
                     'problems': [{'index': 'A', 'points': 1000}],
                     'rows': [{'points': 900}, {'points': 740}, {'points': 500}]}
        submissions = [sub(1, 1000, 1010, 'A', 'WRONG_ANSWER'),
                       sub(1, 1000, 1020, 'A', 'WRONG_ANSWER'),
                       sub(1, 1000, 4000, 'A', 'OK'),
                       sub(1, 99999, 100000, 'A', 'OK')]
        self.assertEqual(estimate_vp_rank(submissions, 1000, standings), 2)

    def test_no_cross_session_submissions(self):
        standings = {'contest': {'type': 'CF', 'durationSeconds': 7200},
                     'problems': [{'index': 'A', 'points': 500}],
                     'rows': [{'points': 100}, {'points': 0}]}
        self.assertEqual(estimate_vp_rank([sub(1, 20000, 20010, 'A', 'OK')], 1000, standings), 2)

    def test_icpc_deduces_10_minute_penalty(self):
        standings = {'contest': {'type': 'ICPC', 'durationSeconds': 7200},
                     'problems': [{'index': 'A'}],
                     'rows': [
                         {'points': 1, 'penalty': 50, 'problemResults': [
                             {'points': 1, 'bestSubmissionTimeSeconds': 1800, 'rejectedAttemptCount': 2}]},
                         {'points': 1, 'penalty': 45, 'problemResults': [
                             {'points': 1, 'bestSubmissionTimeSeconds': 2700, 'rejectedAttemptCount': 0}]}]}
        runs = [sub(1, 1000, 1600, 'A', 'WRONG_ANSWER'),
                sub(1, 1000, 2200, 'A', 'OK')]
        # 20 minutes + 10 minutes = 30, so this run ranks first.
        self.assertEqual(estimate_vp_rank(runs, 1000, standings), 1)

    def test_icpc_tie_not_counted_as_better(self):
        standings = {'contest': {'type': 'ICPC', 'durationSeconds': 7200},
                     'problems': [{'index': 'A'}],
                     'rows': [{'points': 0, 'penalty': 0, 'problemResults': []} for _ in range(6)]}
        self.assertEqual(estimate_vp_rank([], 1000, standings), 1)

    def test_skips_unsupported_ioi(self):
        standings = {'contest': {'type': 'IOI', 'durationSeconds': 7200},
                     'problems': [], 'rows': []}
        self.assertIsNone(estimate_vp_rank([], 1000, standings))

    def test_icpc_deduces_20_minute_penalty(self):
        standings = {'contest': {'type': 'ICPC', 'durationSeconds': 7200},
                     'problems': [{'index': 'A'}],
                     'rows': [
                         {'points': 1, 'penalty': 55, 'problemResults': [
                             {'points': 1, 'bestSubmissionTimeSeconds': 900, 'rejectedAttemptCount': 2}]},
                         {'points': 1, 'penalty': 70, 'problemResults': [
                             {'points': 1, 'bestSubmissionTimeSeconds': 4200, 'rejectedAttemptCount': 0}]}]}
        runs = [sub(1, 1000, 1600, 'A', 'WRONG_ANSWER'),
                sub(1, 1000, 3400, 'A', 'OK')]
        # 40 minutes + 20 minutes = 60, so the first row is better.
        self.assertEqual(estimate_vp_rank(runs, 1000, standings), 2)



if __name__ == '__main__':
    unittest.main()
