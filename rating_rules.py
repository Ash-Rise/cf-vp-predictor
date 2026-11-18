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




def is_rated_simulation_event(event, excluded_vp_ids):
    """Manual VP exclusions do not count; actual official records always do."""
    return event["type"] == "REAL" or event["cid"] not in excluded_vp_ids


def use_new_account_policy(events, excluded_vp_ids=frozenset()):
    """Infer the modern rule from the first *eligible* event in the simulation.

    This is a conservative historical date guard, not a full recreation of
    Codeforces account policy at the May 2020 transition.
    """
    first = next(
        (e for e in sorted(events, key=lambda row: row["ts"])
         if is_rated_simulation_event(e, excluded_vp_ids)),
        None,
    )
    return first is not None and first["ts"] >= NEW_ACCOUNT_POLICY_CUTOFF_TS


def simulation_start_rating(events, excluded_vp_ids=frozenset()):
    """Modern simulated newcomers start internally at 1400; legacy at 100."""
    return (
        INTERNAL_START if use_new_account_policy(events, excluded_vp_ids)
        else DEFAULT_INITIAL_RATING
    )


def display_simulation_rating(internal_rating, rated_contests, modern_policy):
    """Show 0 before the first rated round, then the modeled visible Rating."""
    if rated_contests == 0:
        return 0
    return visible_rating(internal_rating, rated_contests, modern_policy)


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
