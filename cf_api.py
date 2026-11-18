"""Codeforces API access: process-wide pacing, durable caches and incremental status.

The official unauthenticated rate limit is one request per two seconds.
Cache files live in a local, disposable directory; no persistent DB is needed.
"""

import hashlib
import json
import os
import tempfile
import threading
import time
from pathlib import Path

import requests

CACHE_DIR = Path("data") / "cf_api_v2"
BASE = "https://codeforces.com/api/"
MIN_REQUEST_SPACING = 2.1
PERSONAL_TTL = 300
_CACHE_TTL = {
    "contest.ratingChanges": 30 * 86400,
    "contest.standings": 30 * 86400,
    "contest.list": 86400,
    "user.rating": PERSONAL_TTL,
}

_request_lock = threading.Lock()
_last_request_at = 0.0


class CFAPIError(RuntimeError):
    pass


def _path(method, params):
    payload = json.dumps([method, params or {}], sort_keys=True, ensure_ascii=False)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:20]
    safe_method = method.replace(".", "_")
    return CACHE_DIR / f"{safe_method}_{digest}.json"


def _read(path, ttl=None):
    try:
        if ttl is not None and time.time() - path.stat().st_mtime > ttl:
            return None
        with path.open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, ValueError, TypeError):
        return None


def _write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=str(path.parent), delete=False
    ) as stream:
        temporary = Path(stream.name)
        try:
            json.dump(data, stream, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    os.replace(temporary, path)


def _compact(method, result):
    if method == "contest.ratingChanges":
        return [
            {"rank": r["rank"], "oldRating": r["oldRating"], "newRating": r["newRating"]}
            for r in result
        ]
    if method == "contest.list":
        return [
            {"id": c["id"], "startTimeSeconds": c.get("startTimeSeconds"),
             "phase": c.get("phase"), "name": c.get("name")}
            for c in result
        ]
    if method == "contest.standings":
        return {
            "contest": result["contest"],
            "problems": [{"index": p["index"], "points": p.get("points", 0)}
                         for p in result.get("problems", [])],
            "rows": [
                {
                    "points": row.get("points", 0),
                    "penalty": row.get("penalty", 0),
                    "problemResults": [
                        {"points": p.get("points", 0),
                         "rejectedAttemptCount": p.get("rejectedAttemptCount", 0),
                         "bestSubmissionTimeSeconds": p.get("bestSubmissionTimeSeconds", 0)}
                        for p in row.get("problemResults", [])
                    ],
                }
                for row in result.get("rows", [])
            ],
        }
    return result


def _remote(method, params=None):
    global _last_request_at
    last_error = None
    for attempt in range(3):
        with _request_lock:
            remaining = MIN_REQUEST_SPACING - (time.monotonic() - _last_request_at)
            if remaining > 0:
                time.sleep(remaining)
            _last_request_at = time.monotonic()
            try:
                response = requests.get(BASE + method, params=params, timeout=35)
                if response.status_code in (429, 430):
                    last_error = f"HTTP {response.status_code}: rate limit"
                else:
                    response.raise_for_status()
                    payload = response.json()
                    if payload.get("status") == "OK":
                        return payload["result"]
                    last_error = payload.get("comment", "unknown Codeforces API failure")
            except (requests.RequestException, ValueError, KeyError) as exc:
                last_error = str(exc)
        if attempt < 2:
            time.sleep(2 * (attempt + 1))
    raise CFAPIError(f"Codeforces API {method} failed: {last_error}")


def get_json(method, params=None, *, force=False):
    """Fetch an API method, with shared disk cache for reusable responses."""
    ttl = _CACHE_TTL.get(method)
    path = _path(method, params)
    if not force and ttl is not None:
        cached = _read(path, ttl=ttl)
        if cached is not None:
            return cached
    value = _compact(method, _remote(method, params))
    if ttl is not None:
        _write(path, value)
    return value


def _personal_path(handle):
    return _path("personal.submissions", {"handle": handle.casefold()})


def get_user_submissions(handle):
    """First fetch full history; later fetch only newly submitted/recent entries.

    Overlap with 200 recent submissions refreshes pending verdicts. Page until
    an existing submission ID is observed, so >200 new submissions are not lost.
    """
    path = _personal_path(handle)
    state = _read(path)
    if state and time.time() - state.get("fetched", 0) < PERSONAL_TTL:
        return state["submissions"]

    old = state.get("submissions", []) if isinstance(state, dict) else []
    if not old:
        rows = _remote("user.status", {"handle": handle})
    else:
        old_ids = {row.get("id") for row in old}
        updates = []
        offset = 1
        while True:
            page = _remote("user.status", {"handle": handle, "from": offset, "count": 200})
            if not page:
                break
            updates.extend(page)
            if any(row.get("id") in old_ids for row in page) or len(page) < 200:
                break
            offset += len(page)
            if offset > 20000:
                raise CFAPIError("Submission catch-up exceeds 20,000 new submissions")
        by_id = {row["id"]: row for row in old if isinstance(row.get("id"), int)}
        for row in updates:
            if isinstance(row.get("id"), int):
                by_id[row["id"]] = row
        rows = sorted(by_id.values(), key=lambda row: row["id"], reverse=True)
    _write(path, {"fetched": time.time(), "submissions": rows})
    return rows


def clear_personal_cache(handle):
    """Do not delete other users' cached history or immutable contest data."""
    paths = [_personal_path(handle), _path("user.rating", {"handle": handle})]
    for path in paths:
        path.unlink(missing_ok=True)
