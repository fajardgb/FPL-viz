"""
fpl_client.py — async FPL API access: input validation, fetching, and the
league-size cap. No caching and no data-shaping lives here; see cache.py and
analysis.py respectively.
"""
import asyncio
from typing import Optional

import httpx

FPL_BASE = "https://fantasy.premierleague.com/api"
MAX_LEAGUE_SIZE = 200
STANDINGS_PAGE_SIZE = 50  # FPL's own page size for the classic-league standings endpoint


class FPLError(Exception):
    """A user-facing problem: bad input, unknown league, or a league too large to serve."""


# ── Validation ────────────────────────────────────────────────────────────────

def validate_league_id(raw: str) -> int:
    try:
        league_id = int(str(raw).strip())
    except (TypeError, ValueError):
        raise FPLError(f"League ID must be a whole number. Got {raw!r}.")
    if league_id <= 0:
        raise FPLError(f"League ID must be a positive number. Got {league_id}.")
    return league_id


def validate_gameweek(raw, bootstrap: dict) -> int:
    try:
        gw = int(str(raw).strip())
    except (TypeError, ValueError):
        raise FPLError(f"Gameweek must be a whole number. Got {raw!r}.")
    valid_ids = {event["id"] for event in bootstrap.get("events", [])}
    if gw not in valid_ids:
        max_gw = max(valid_ids) if valid_ids else 38
        raise FPLError(f"GW{gw} does not exist this season. Use a value from 1 to {max_gw}.")
    return gw


def get_event_info(bootstrap: dict, gw: int) -> dict:
    return next(e for e in bootstrap["events"] if e["id"] == gw)


def current_gameweek(bootstrap: dict) -> int:
    events = bootstrap.get("events", [])
    for e in events:
        if e.get("is_current"):
            return e["id"]
    for e in events:
        if e.get("is_next"):
            return max(1, e["id"] - 1)
    return max((e["id"] for e in events), default=1)


# ── Bootstrap / standings ──────────────────────────────────────────────────────

async def fetch_bootstrap(client: httpx.AsyncClient) -> dict:
    resp = await client.get(f"{FPL_BASE}/bootstrap-static/", timeout=30)
    resp.raise_for_status()
    return resp.json()


async def fetch_league(client: httpx.AsyncClient, league_id: int, max_size: int = MAX_LEAGUE_SIZE) -> dict:
    """
    Fetch a classic league's standings, paginating only far enough to learn
    whether it's within max_size — this is the cheap check that runs *before*
    any per-manager fetching.

    Returns either {"oversized": True, "count": N} or
    {"oversized": False, "league": {...}, "standings_results": [...], "new_entries_results": [...]}.
    """
    page = 1
    all_results: list[dict] = []
    league_meta: Optional[dict] = None
    new_entries_results: list[dict] = []

    while True:
        resp = await client.get(
            f"{FPL_BASE}/leagues-classic/{league_id}/standings/",
            params={"page_standings": page},
            timeout=30,
        )
        if resp.status_code == 404:
            raise FPLError(f"League {league_id} was not found.")
        resp.raise_for_status()
        data = resp.json()

        if league_meta is None:
            league_meta = data.get("league", {})
            new_entries_results = data.get("new_entries", {}).get("results", [])

        standings = data.get("standings", {})
        all_results.extend(standings.get("results", []))

        if len(all_results) > max_size:
            return {"oversized": True, "count": len(all_results)}
        if not standings.get("has_next"):
            break
        page += 1

    return {
        "oversized": False,
        "league": league_meta,
        "standings_results": all_results,
        "new_entries_results": new_entries_results,
    }


def entry_to_player_mapping(league_data: dict) -> dict[int, str]:
    """Before GW1, membership lives in new_entries; after that, in standings."""
    results = league_data.get("new_entries_results") or []
    if results:
        return {r["entry"]: f"{r['player_first_name']} {r['player_last_name']}" for r in results}
    results = league_data.get("standings_results") or []
    return {r["entry"]: r["player_name"] for r in results}


def check_league_size(league_data: dict) -> None:
    if league_data.get("oversized"):
        raise FPLError(
            f"This league has more than {MAX_LEAGUE_SIZE} managers "
            f"(reports aren't supported yet for leagues that large)."
        )


# ── Per-manager fetching (concurrent) ───────────────────────────────────────────

async def _get_json(client: httpx.AsyncClient, url: str) -> Optional[dict]:
    try:
        resp = await client.get(url, timeout=30)
    except httpx.HTTPError:
        return None
    if resp.status_code != 200:
        return None
    return resp.json()


async def fetch_histories(client: httpx.AsyncClient, entry_ids: list[int]) -> dict[int, Optional[dict]]:
    urls = [f"{FPL_BASE}/entry/{eid}/history/" for eid in entry_ids]
    results = await asyncio.gather(*[_get_json(client, u) for u in urls])
    return dict(zip(entry_ids, results))


async def fetch_picks_for_gw(client: httpx.AsyncClient, entry_ids: list[int], gw: int) -> dict[int, Optional[dict]]:
    urls = [f"{FPL_BASE}/entry/{eid}/event/{gw}/picks/" for eid in entry_ids]
    results = await asyncio.gather(*[_get_json(client, u) for u in urls])
    return dict(zip(entry_ids, results))
