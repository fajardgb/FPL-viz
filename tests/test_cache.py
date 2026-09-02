import json
from pathlib import Path

from app import cache

FIXTURES = Path(__file__).parent / "fixtures"


def load_bootstrap():
    return json.loads((FIXTURES / "bootstrap_static.json").read_text())


def test_finished_gw_cached_forever():
    bootstrap = load_bootstrap()
    finished_event = next(e for e in bootstrap["events"] if e["id"] == 1)
    assert cache.gw_ttl(finished_event) is None


def test_live_gw_has_short_ttl():
    bootstrap = load_bootstrap()
    live_event = next(e for e in bootstrap["events"] if e["id"] == 3)
    assert cache.gw_ttl(live_event) == cache.LIVE_GW_TTL_SECONDS


def test_future_gw_has_short_ttl():
    bootstrap = load_bootstrap()
    future_event = next(e for e in bootstrap["events"] if e["id"] == 4)
    assert cache.gw_ttl(future_event) == cache.LIVE_GW_TTL_SECONDS


def test_missing_event_info_defaults_to_short_ttl():
    assert cache.gw_ttl(None) == cache.LIVE_GW_TTL_SECONDS


def test_make_key_is_stable_and_scoped():
    assert cache.make_key(123, 4, "league") == "123:4:league"
    assert cache.make_key(123, 5, "league") != cache.make_key(123, 4, "league")
