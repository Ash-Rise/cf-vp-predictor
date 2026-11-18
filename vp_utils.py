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


def reconstruct_vp_result(submissions, start, standings):
    """Return estimated rank, points/penalty, solved problems and submission details.

    This is a simulation against the historical official ranklist, not an
    official Codeforces result. Hacks and some special rules are not modeled.
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
    for sub in sorted(submissions, key=lambda row: row.get("creationTimeSeconds", 0)):
        ts = sub.get("creationTimeSeconds")
        if not isinstance(ts, int) or not (0 <= ts - start < duration_s):
            continue
        pid = (sub.get("problem") or {}).get("index")
        if not pid or pid in accepted:
            continue
        verdict = sub.get("verdict")
        if verdict == "OK":
            accepted[pid] = ((ts - start) // 60, wrong[pid])
        elif verdict not in (None, "COMPILATION_ERROR", "TESTING", "SKIPPED"):
            wrong[pid] += 1

    penalty = None
    if scoring == "ICPC":
        points = len(accepted)
        penalty_per_wa = _wa_penalty_minutes(standings["rows"])
        penalty = sum(mins + attempts * penalty_per_wa for mins, attempts in accepted.values())
        better = sum(
            row["points"] > points or
            (row["points"] == points and row.get("penalty", 0) < penalty)
            for row in standings["rows"]
        )
    else:
        full = {p["index"]: p.get("points", 0) for p in standings["problems"]}
        points = sum(
            max(0.3 * full[pid], full[pid] -
                floor(120 * full[pid] * mins / (250 * duration_m)) - 50 * attempts)
            for pid, (mins, attempts) in accepted.items()
            if full.get(pid, 0) > 0
        )
        better = sum(row["points"] > points for row in standings["rows"])

    return {
        "rank": better + 1, "score": round(points, 2),
        "solved": len(accepted), "penalty": penalty, "scoring": scoring,
        "problems": [
            {"problem": pid, "minute": mins, "wrong_attempts": attempts}
            for pid, (mins, attempts) in sorted(accepted.items())
        ],
    }


def estimate_vp_rank(submissions, start, standings):
    """Backwards-compatible rank-only interface used by existing tests."""
    details = reconstruct_vp_result(submissions, start, standings)
    return details["rank"] if details is not None else None
