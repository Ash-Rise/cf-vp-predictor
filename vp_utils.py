"""Pure helpers for reconstructing Codeforces virtual participation standings."""

from collections import defaultdict
from math import floor


def group_vp_sessions(submissions):
    """Return (contest_id, start_timestamp, submissions) for each virtual run.

    Prefer Codeforces' actual startTimeSeconds over guessing from submission gaps.
    Older/incomplete records without a start timestamp use the prior 48-hour
    heuristic as a fallback only.
    """
    runs = defaultdict(list)
    without_start = defaultdict(list)
    for sub in submissions or []:
        author = sub.get("author") or {}
        if author.get("participantType") != "VIRTUAL":
            continue
        cid = sub.get("contestId")
        ts = sub.get("creationTimeSeconds")
        if not isinstance(cid, int) or not isinstance(ts, int):
            continue
        start = author.get("startTimeSeconds")
        if isinstance(start, int) and start > 0:
            runs[(cid, start)].append(sub)
        else:
            without_start[cid].append(sub)

    for cid, items in without_start.items():
        items.sort(key=lambda s: s["creationTimeSeconds"])
        previous = None
        start = None
        for sub in items:
            ts = sub["creationTimeSeconds"]
            if previous is None or ts - previous > 48 * 3600:
                start = ts
            runs[(cid, start)].append(sub)
            previous = ts

    result = [
        (cid, start, sorted(items, key=lambda s: s["creationTimeSeconds"]))
        for (cid, start), items in runs.items()
    ]
    return sorted(result, key=lambda run: (run[1], run[0]))


def _wa_penalty_minutes(rows):
    """Infer 10/20-minute ICPC penalty from accepted problems on official rows.

    Codeforces has run both types of ICPC-style contests. If there is no
    evidence, preserve the original app's 20-minute convention.
    """
    votes = {10: 0, 20: 0}
    for row in rows:
        solved = [p for p in row.get("problemResults", []) if p.get("points", 0) > 0]
        wrong = sum(p.get("rejectedAttemptCount", 0) for p in solved)
        if not wrong:
            continue
        mins = sum(int(p.get("bestSubmissionTimeSeconds", 0)) // 60 for p in solved)
        rate = (row.get("penalty", 0) - mins) / wrong
        for candidate in votes:
            if abs(rate - candidate) <= 1:
                votes[candidate] += 1
    return 10 if votes[10] > votes[20] else 20


def estimate_vp_rank(submissions, start, standings):
    """Return an estimated official rank, or None for unsupported scoring.

    Uses only submissions inside this session's contest duration. This still
    cannot perfectly reconstruct hacks, partial scoring, or unofficial entries.
    """
    contest = standings["contest"]
    scoring = contest.get("type", "CF")
    if scoring not in ("CF", "ICPC"):
        return None
    duration_s = contest.get("durationSeconds", 7200)
    duration_m = duration_s / 60
    if duration_m <= 0:
        return None

    accepted = {}
    wrong = defaultdict(int)
    for sub in sorted(submissions, key=lambda s: s.get("creationTimeSeconds", 0)):
        ts = sub.get("creationTimeSeconds")
        if not isinstance(ts, int) or not (0 <= ts - start < duration_s):
            continue
        problem = sub.get("problem") or {}
        pid = problem.get("index")
        if not pid or pid in accepted:
            continue
        verdict = sub.get("verdict")
        if verdict == "OK":
            accepted[pid] = ((ts - start) // 60, wrong[pid])
        elif verdict not in (None, "COMPILATION_ERROR", "TESTING", "SKIPPED"):
            wrong[pid] += 1

    if scoring == "ICPC":
        pts = len(accepted)
        per_wrong = _wa_penalty_minutes(standings["rows"])
        penalty = sum(t + w * per_wrong for t, w in accepted.values())
        better = sum(
            row["points"] > pts or (row["points"] == pts and row["penalty"] < penalty)
            for row in standings["rows"]
        )
    else:
        full_points = {p["index"]: p.get("points", 0) for p in standings["problems"]}
        pts = sum(
            max(0.3 * full_points[pid], full_points[pid] - floor(120 * full_points[pid] * t / (250 * duration_m)) - 50 * w)
            for pid, (t, w) in accepted.items() if full_points.get(pid, 0) > 0
        )
        better = sum(row["points"] > pts for row in standings["rows"])
    return better + 1
