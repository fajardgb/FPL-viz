import httpx
import pytest
import respx

from app.fpl_client import (
    FPLError,
    check_league_size,
    entry_to_player_mapping,
    fetch_league,
    validate_gameweek,
    validate_league_id,
)

LEAGUE_URL = "https://fantasy.premierleague.com/api/leagues-classic/999/standings/"


def _page(results, has_next):
    return {
        "league": {"id": 999, "name": "Test League"},
        "new_entries": {"results": []},
        "standings": {"results": results, "has_next": has_next},
    }


def _managers(n, start=0):
    return [{"entry": i, "player_name": f"Manager {i}"} for i in range(start, start + n)]


@pytest.mark.asyncio
@respx.mock
async def test_small_league_is_not_oversized():
    respx.get(LEAGUE_URL).mock(return_value=httpx.Response(200, json=_page(_managers(18), has_next=False)))
    async with httpx.AsyncClient() as client:
        data = await fetch_league(client, 999, max_size=200)

    assert data["oversized"] is False
    check_league_size(data)  # should not raise
    mapping = entry_to_player_mapping(data)
    assert len(mapping) == 18


@pytest.mark.asyncio
@respx.mock
async def test_league_over_cap_stops_paginating_and_is_rejected():
    # 5 pages of 50 = 250 managers, over a cap of 200 — should stop after page 5 (250 > 200).
    route = respx.get(LEAGUE_URL)
    route.side_effect = [
        httpx.Response(200, json=_page(_managers(50, start=i * 50), has_next=True)) for i in range(4)
    ] + [httpx.Response(200, json=_page(_managers(50, start=200), has_next=True))]

    async with httpx.AsyncClient() as client:
        data = await fetch_league(client, 999, max_size=200)

    assert data["oversized"] is True
    with pytest.raises(FPLError):
        check_league_size(data)
    # Only fetched 5 pages, not continuing indefinitely just because has_next was still True.
    assert route.call_count == 5


@pytest.mark.asyncio
@respx.mock
async def test_unknown_league_raises_fpl_error():
    respx.get(LEAGUE_URL).mock(return_value=httpx.Response(404))
    async with httpx.AsyncClient() as client:
        with pytest.raises(FPLError):
            await fetch_league(client, 999, max_size=200)


def test_validate_league_id_rejects_non_numeric():
    with pytest.raises(FPLError):
        validate_league_id("not-a-number")
    with pytest.raises(FPLError):
        validate_league_id("-5")
    assert validate_league_id("1078291") == 1078291
    assert validate_league_id(" 42 ") == 42


def test_validate_league_id_rejects_path_traversal_input():
    with pytest.raises(FPLError):
        validate_league_id("../../etc/passwd")


def test_validate_gameweek_rejects_out_of_range():
    bootstrap = {"events": [{"id": 1}, {"id": 2}, {"id": 3}]}
    with pytest.raises(FPLError):
        validate_gameweek("99", bootstrap)
    with pytest.raises(FPLError):
        validate_gameweek("nope", bootstrap)
    assert validate_gameweek("2", bootstrap) == 2
