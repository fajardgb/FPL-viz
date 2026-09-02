import pandas as pd

from app import analysis


def make_history(points_per_gw: list[int]) -> dict:
    return {"current": [{"event": i + 1, "points": p} for i, p in enumerate(points_per_gw)]}


def test_build_gw_history_df_is_cumulative():
    entry_to_player = {1: "Alice", 2: "Bob"}
    histories = {
        1: make_history([10, 20, 5]),
        2: make_history([5, 5, 5]),
    }
    df = analysis.build_gw_history_df(entry_to_player, histories)

    assert list(df["GW"]) == ["GW1", "GW2", "GW3"]
    assert list(df["Alice"]) == [10, 30, 35]
    assert list(df["Bob"]) == [5, 10, 15]


def test_build_gw_history_df_skips_managers_with_no_history():
    entry_to_player = {1: "Alice", 2: "Bob"}
    histories = {1: make_history([10, 20]), 2: None}
    df = analysis.build_gw_history_df(entry_to_player, histories)
    assert "Alice" in df.columns
    assert "Bob" not in df.columns


def test_get_standings_for_gw_ranks_by_points_desc():
    df = pd.DataFrame({"GW": ["GW1", "GW2"], "Alice": [10, 30], "Bob": [5, 40]})
    standings = analysis.get_standings_for_gw(df, 2)

    assert list(standings["player_name"]) == ["Bob", "Alice"]
    assert list(standings["rank"]) == [1, 2]
    assert list(standings["total_points"]) == [40, 30]


def test_get_standings_for_gw_missing_gw_returns_empty():
    df = pd.DataFrame({"GW": ["GW1"], "Alice": [10]})
    standings = analysis.get_standings_for_gw(df, 5)
    assert standings.empty


def test_top3_ranking_history_identifies_leaders_and_tenure():
    df = pd.DataFrame(
        {
            "GW": ["GW1", "GW2", "GW3"],
            "Alice": [10, 20, 50],
            "Bob": [30, 35, 40],
            "Carl": [5, 60, 20],
            "Dee": [1, 2, 3],
        }
    )
    result = analysis.get_top3_ranking_history(df)

    assert set(result["top3_names"]) == {"Alice", "Bob", "Carl"}
    assert "Dee" not in result["top3_names"]

    stats = result["rank_stats"].set_index("player_name")
    # Alice's ranks across GW1-3 are 2, 3, 1 -> 1 week at #1, all 3 weeks in top3
    assert stats.loc["Alice", "weeks_at_rank1"] == 1
    assert stats.loc["Alice", "weeks_in_top3"] == 3


def test_player_mappings_from_bootstrap():
    bootstrap = {
        "elements": [
            {"id": 1, "web_name": "Salah", "now_cost": 130, "total_points": 200},
            {"id": 2, "web_name": "Haaland", "now_cost": 150, "total_points": 250},
        ]
    }
    to_id, to_price, to_points = analysis.player_mappings(bootstrap)
    assert to_id == {1: "Salah", 2: "Haaland"}
    assert to_price == {1: 130, 2: 150}
    assert to_points == {1: 200, 2: 250}


def test_build_team_summary_counts_ownership_and_captaincy():
    picks_by_entry = {
        1: {"picks": [{"element": 1, "is_captain": True}, {"element": 2, "is_captain": False}]},
        2: {"picks": [{"element": 1, "is_captain": False}]},
        3: None,
    }
    player_to_id = {1: "Salah", 2: "Haaland"}
    player_to_price = {1: 130, 2: 150}
    player_to_points = {1: 200, 2: 250}

    df = analysis.build_team_summary(picks_by_entry, player_to_id, player_to_price, player_to_points)
    salah = df[df["player_name"] == "Salah"].iloc[0]
    assert salah["own_count"] == 2
    assert salah["captaincy_count"] == 1


def test_build_transfers_diffs_squads():
    prev = {1: {"picks": [{"element": 1}, {"element": 2}]}}
    curr = {1: {"picks": [{"element": 1}, {"element": 3}]}}
    player_to_id = {1: "A", 2: "B", 3: "C"}

    df_in, df_out = analysis.build_transfers(prev, curr, player_to_id)
    assert list(df_in["player_name"]) == ["C"]
    assert list(df_out["player_name"]) == ["B"]


def test_get_active_chips_ignores_managers_without_a_chip():
    picks_by_entry = {
        1: {"active_chip": "wildcard"},
        2: {"active_chip": None},
        3: None,
    }
    assert analysis.get_active_chips(picks_by_entry) == ["wildcard"]
