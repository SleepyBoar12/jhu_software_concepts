"""Enforce a shared upper bound on rows returned by database queries."""

MAX_QUERY_LIMIT = 50


def clamp_query_limit(limit=MAX_QUERY_LIMIT):
    """Accept an integer limit, clamp it to 1–50, and reject malformed input."""
    if isinstance(limit, bool) or not isinstance(limit, (int, str)):
        raise ValueError("limit must be an integer")
    try:
        number = int(limit)
    except ValueError as error:
        raise ValueError("limit must be an integer") from error
    return max(1, min(number, MAX_QUERY_LIMIT))
