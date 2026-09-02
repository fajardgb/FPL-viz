"""
cache.py — disk-backed cache for FPL API responses and generated report
artifacts. Keyed on (league_id, gw, artifact name). TTL depends on whether
that gameweek has finished: forever once finished, a few minutes while live.
"""
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

import diskcache

BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
OUTPUT_DIR = CACHE_DIR / "output"

LIVE_GW_TTL_SECONDS = 300  # 5 minutes

_cache = diskcache.Cache(str(CACHE_DIR))


def gw_ttl(event_info: Optional[dict]) -> Optional[int]:
    """None means cache forever; a finished gameweek's data never changes."""
    if event_info and event_info.get("finished"):
        return None
    return LIVE_GW_TTL_SECONDS


def make_key(league_id: int, gw: int, name: str) -> str:
    return f"{league_id}:{gw}:{name}"


def report_output_dir(league_id: int, gw: int) -> Path:
    path = OUTPUT_DIR / f"league_{league_id}" / f"GW{gw}"
    path.mkdir(parents=True, exist_ok=True)
    return path


async def get_or_fetch(key: str, ttl: Optional[int], fetch: Callable[[], Awaitable[Any]]) -> Any:
    if key in _cache:
        return _cache[key]
    value = await fetch()
    _cache.set(key, value, expire=ttl)
    return value


def get(key: str, default: Any = None) -> Any:
    return _cache.get(key, default)


def set(key: str, value: Any, ttl: Optional[int]) -> None:
    _cache.set(key, value, expire=ttl)
