"""Small, testable rules for interpreting a hypothetical Codeforces rating path."""

# Official public newcomer-display bonuses after rated contests 1 through 6.
# The *internal* rating starts at 1400; display starts at 0.
NEWCOMER_BONUSES = (500, 350, 250, 150, 100, 50)
INTERNAL_START = 1400


def visible_rating(internal_rating, rated_contests, newcomer_mode=False):
    """Apply the official six-round display adjustment when explicitly enabled."""
    if not newcomer_mode:
        return internal_rating
    applied = sum(NEWCOMER_BONUSES[:max(0, rated_contests)])
    return internal_rating - (INTERNAL_START - applied)


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
