"""Pure rating-path simulation and inspectable five-proxy explanations."""

from datetime import datetime, timezone

from rating_rules import (
    display_simulation_rating,
    simulation_start_rating,
    use_new_account_policy,
)


def build_official_events(rating_history, contest_starts):
    """Use contest START times for model order, not later Rating update timestamps."""
    events = []
    official_curve = []
    missing_start = 0
    for item in rating_history:
        cid = item["contestId"]
        updated = item["ratingUpdateTimeSeconds"]
        started = contest_starts.get(cid)
        if not started:
            started = updated
            missing_start += 1
        events.append({
            "key": f"REAL:{cid}:{updated}", "cid": cid,
            "ts": started, "type": "REAL", "rank": item["rank"],
            "name": item["contestName"],
        })
        official_curve.append({
            "date": datetime.fromtimestamp(updated, timezone.utc),
            "rating": item["newRating"], "name": item["contestName"],
            "rank": item["rank"],
        })
    return events, official_curve, missing_start


def estimate_delta(internal_rating, rank, rating_changes):
    """Retain the original five-neighbor estimator, expose the proxies it used."""
    candidates = [
        row for row in rating_changes if abs(row["oldRating"] - internal_rating) < 300
    ]
    if not candidates:
        candidates = rating_changes
    scored = sorted(
        enumerate(candidates),
        key=lambda item: (
            abs(item[1]["oldRating"] - internal_rating) * 0.8
            + abs(item[1]["rank"] - rank) * 1.5,
            item[0],
        ),
    )[:5]
    if not scored:
        return None, []

    proxies = []
    for _, row in scored:
        distance = (
            abs(row["oldRating"] - internal_rating) * 0.8
            + abs(row["rank"] - rank) * 1.5
        )
        true_delta = row["newRating"] - row["oldRating"]
        rank_correction = 1 if rank < row["rank"] else -1 if rank > row["rank"] else 0
        proxies.append({
            "Handle": row.get("handle", ""),
            "Profile": f"https://codeforces.com/profile/{row['handle']}" if row.get("handle") else "",
            "Pre-contest Rating": row["oldRating"],
            "Rank": row["rank"],
            "Official Delta": true_delta,
            "Rank adjustment": rank_correction,
            "Adjusted Delta": true_delta + rank_correction,
            "Distance": round(distance, 2),
        })
    values = sorted(p["Adjusted Delta"] for p in proxies)
    if len(values) >= 3:
        values = values[1:-1]
    return round(sum(values) / len(values)), proxies


def simulate(events, changes_by_cid, excluded_vp_keys=frozenset(), *, include_vp=True):
    """Compute a rating path with identical model/policy for both scenarios.

    Two runs, one with and one without VP, isolate VP's *modeled* contribution.
    A skipped contest with missing rating changes is explicitly reported.
    """
    eligible = [
        event for event in events
        if event["type"] == "REAL" or event["key"] not in excluded_vp_keys
    ]
    modern = use_new_account_policy(eligible)
    # Same initial rating for both counterfactual paths.
    internal = simulation_start_rating(eligible)
    counted = 0
    history = []
    unavailable = []

    if events:
        history.append({
            "key": "INITIAL", "cid": None,
            "date": datetime.fromtimestamp(events[0]["ts"] - 86400, timezone.utc),
            "rating": 0, "type": "INIT", "name": "Start",
            "rank": 0, "delta": 0, "model_delta": 0, "proxies": [],
        })

    for event in events:
        if event["type"] == "VP" and not include_vp:
            continue
        old_display = display_simulation_rating(internal, counted, modern)
        is_unrated = event["type"] == "VP" and event["key"] in excluded_vp_keys
        changes = changes_by_cid.get(event["cid"])
        predicted, proxies = (
            (0, []) if is_unrated
            else estimate_delta(internal, event["rank"], changes) if changes else (None, [])
        )
        if predicted is None:
            unavailable.append(event["key"])
            predicted = 0
        elif not is_unrated:
            internal += predicted
            counted += 1

        visible = display_simulation_rating(internal, counted, modern)
        history.append({
            "key": event["key"], "cid": event["cid"],
            "date": datetime.fromtimestamp(event["ts"], timezone.utc),
            "type": event["type"], "name": event["name"],
            "rank": event["rank"], "rating": visible,
            "delta": visible - old_display,
            "model_delta": predicted,
            "proxies": proxies,
            "unrated": is_unrated,
            "unavailable": event["key"] in unavailable,
            "internal_before": internal - predicted,
            "internal_after": internal,
            "rated_count": counted,
            "vp_details": event.get("vp_details"),
        })
    return history, unavailable


def modeled_vp_contribution(with_vp, without_vp):
    """A counterfactual difference, not an exact official Codeforces Delta."""
    return (
        (with_vp[-1]["rating"] if with_vp else 0)
        - (without_vp[-1]["rating"] if without_vp else 0)
    )
