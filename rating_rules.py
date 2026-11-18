"""Small, testable rules for interpreting a hypothetical Codeforces rating path."""

from datetime import datetime, timezone

# Official public newcomer-display bonuses after rated contests 1 through 6.
# The *internal* rating starts at 1400; display starts at 0.
NEWCOMER_BONUSES = (500, 350, 250, 150, 100, 50)
INTERNAL_START = 1400
DEFAULT_INITIAL_RATING = 100
# Conservative boundary: the new-account policy was introduced around May 2020.
# Historical transition-month contests require separate validation.
NEW_ACCOUNT_POLICY_CUTOFF_TS = int(datetime(2020, 6, 1, tzinfo=timezone.utc).timestamp())


def visible_rating(internal_rating, rated_contests, newcomer_mode=False):
    """Apply the official six-round display adjustment when explicitly enabled."""
    if not newcomer_mode:
        return internal_rating
    applied = sum(NEWCOMER_BONUSES[:max(0, rated_contests)])
    return internal_rating - (INTERNAL_START - applied)




def use_new_account_policy(events):
    """Choose policy automatically from the earliest chronological rated event.

    The modern policy is only applied to simulated histories starting in/after
    June 2020; older historical accounts retain the legacy approximation.
    """
    return bool(events) and min(e["ts"] for e in events) >= NEW_ACCOUNT_POLICY_CUTOFF_TS


def simulation_start_rating(events):
    """Start modern accounts internally at 1400 while preserving a 100-point chart anchor."""
    return INTERNAL_START if use_new_account_policy(events) else DEFAULT_INITIAL_RATING


def display_simulation_rating(internal_rating, rated_contests, modern_policy):
    """Show the requested 100-point graph anchor, then official-style newcomer display values.

    Codeforces itself starts at displayed 0 (not 100); the first computed
    post-contest value is still 500 + estimated internal Delta.
    """
    if modern_policy and rated_contests == 0:
        return DEFAULT_INITIAL_RATING
    return visible_rating(internal_rating, rated_contests, modern_policy)


def is_rated_simulation_event(event, excluded_vp_ids):
    """Manually excluded VPs are not rated; REAL events always are."""
    return event["type"] == "REAL" or event["cid"] not in excluded_vp_ids

def parse_unrated_vp_ids(text):
    """Parse an explicit user override; never infer a cutoff from other entrants."""
    if not text.strip():
        return frozenset()
    result = set()
    for token in text.replace("，", ",").split(","):
        token = token.strip()
        if not token:
            continue
        if not token.isascii() or not token.isdigit():
            raise ValueError(f"Invalid contest ID: {token}")
        result.add(int(token))
    return frozenset(result)
