"""Reproducible leave-one-out evaluation of the existing rating Delta heuristic.

Usage:
    python backtest.py
    python backtest.py --contests 1850 1870 1890 1900 1920 1930 1950

Requires Codeforces API access; requests use the same paced/cached client
as the application. Prints both an aggregate report and per-contest errors.
This is validation, not parameter optimization.
"""
import argparse
import json
import math
import statistics

from cf_api import CFAPIError, get_json
from predictor_core import estimate_delta

DEFAULT_IDS = (1850, 1860, 1870, 1890, 1900, 1915, 1920, 1930, 1950, 1960)


def evaluate_contest(changes, sample_size=25):
    """Compare estimated Delta against official Delta; exclude target itself.

    Deterministic, spread-out sampling across the official ranklist.
    Ignore new accounts (<400 rating) where visible-rating rules differ.
    """
    eligible = [
        p for p in changes
        if p["rank"] > 0 and 400 <= p["oldRating"] <= 3000
    ]
    eligible.sort(key=lambda p: (p["rank"], p.get("handle", "")))
    if not eligible:
        return []
    count = min(len(eligible), sample_size)
    selected = [eligible[int((i + 0.5) * len(eligible) / count)] for i in range(count)]
    results = []
    for target in selected:
        others = [p for p in changes if p is not target]
        if target.get("handle"):
            others = [p for p in others if p.get("handle") != target["handle"]]
        estimate, _ = estimate_delta(target["oldRating"], target["rank"], others)
        if estimate is None:
            continue
        actual = target["newRating"] - target["oldRating"]
        results.append({
            "handle": target.get("handle", ""), "rating": target["oldRating"],
            "rank": target["rank"], "prediction": estimate,
            "actual": actual, "error": estimate - actual,
        })
    return results


def summarize(records):
    errors = [record["error"] for record in records]
    if not errors:
        return {"sample_size": 0, "mae": None, "p90_abs_error": None, "bias": None}
    ordered = sorted(abs(e) for e in errors)
    return {
        "sample_size": len(errors),
        "mae": round(statistics.mean(abs(e) for e in errors), 2),
        "p90_abs_error": ordered[math.ceil(0.9 * len(ordered)) - 1],
        "bias": round(statistics.mean(errors), 2),
    }


def run(contest_ids=DEFAULT_IDS, sample_size=25):
    all_records = []
    per_contest = []
    errors = []
    for cid in contest_ids:
        try:
            changes = get_json("contest.ratingChanges", {"contestId": cid})
        except CFAPIError as exc:
            errors.append({"contest_id": cid, "reason": str(exc)})
            continue
        if not changes:
            errors.append({"contest_id": cid, "reason": "No official rating changes"})
            continue
        rows = evaluate_contest(changes, sample_size=sample_size)
        per_contest.append({"contest_id": cid, **summarize(rows)})
        all_records.extend(rows)
    return {
        "method": "leave-one-out, 5 proxy participants, 25 rank-spaced samples/contest",
        "total": summarize(all_records),
        "contests": per_contest,
        "unavailable_contests": errors,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contests", nargs="+", type=int, default=DEFAULT_IDS)
    parser.add_argument("--sample-size", type=int, default=25)
    args = parser.parse_args()
    if args.sample_size < 1:
        parser.error("--sample-size must be positive")
    print(json.dumps(run(args.contests, args.sample_size), ensure_ascii=False, indent=2))
