"""
analysis.py — pure data transforms: raw FPL API responses (already fetched by
fpl_client) become the DataFrames/dicts the report and charts need. No network
calls live here.
"""
import statistics
from typing import Optional

import pandas as pd


# ── Player mappings (from bootstrap-static) ─────────────────────────────────────

def player_mappings(bootstrap: dict) -> tuple[dict[int, str], dict[int, int], dict[int, int]]:
    """{player_id -> web_name}, {player_id -> now_cost}, {player_id -> total_points}."""
    player_to_id, player_to_price, player_to_points = {}, {}, {}
    for player in bootstrap.get("elements", []):
        pid = player["id"]
        player_to_id[pid] = player["web_name"]
        player_to_price[pid] = player["now_cost"]
        player_to_points[pid] = player["total_points"]
    return player_to_id, player_to_price, player_to_points


# ── GW history / standings ──────────────────────────────────────────────────────

def build_gw_history_df(entry_to_player: dict[int, str], histories: dict[int, Optional[dict]]) -> pd.DataFrame:
    """Cumulative-points-per-GW DataFrame. Columns: GW, <player_name>, ..."""
    n_gws_list = [len(h["current"]) for h in histories.values() if h]
    if not n_gws_list:
        return pd.DataFrame({"GW": []})
    n_gws = statistics.mode(n_gws_list)

    gw_history_df = pd.DataFrame({"GW": [f"GW{gw}" for gw in range(1, n_gws + 1)]})
    for entry, player_name in entry_to_player.items():
        history = histories.get(entry)
        if not history:
            continue
        cumulative = 0
        cum_points = []
        for game in history["current"][:n_gws]:
            cumulative += game["points"]
            cum_points.append(cumulative)
        if not cum_points:
            continue
        while len(cum_points) < n_gws:
            cum_points.append(cum_points[-1])
        gw_history_df[player_name] = cum_points
    return gw_history_df


def get_standings_for_gw(gw_history_df: pd.DataFrame, gw: int) -> pd.DataFrame:
    """Standings table (player_name, rank, total_points) as of a specific GW."""
    gw_col = f"GW{gw}"
    if gw_history_df.empty or gw_col not in gw_history_df["GW"].values:
        return pd.DataFrame(columns=["player_name", "rank", "total_points"])

    standings_list = []
    for player_name in gw_history_df.columns:
        if player_name == "GW":
            continue
        points = gw_history_df.loc[gw_history_df["GW"] == gw_col, player_name].values
        if len(points) > 0:
            standings_list.append({"player_name": player_name, "total_points": int(points[0])})

    df = pd.DataFrame(standings_list).sort_values("total_points", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df[["player_name", "rank", "total_points"]]


def get_top3_ranking_history(gw_history_df: pd.DataFrame) -> dict:
    """
    Top 3 managers' rank history across all gameweeks.

    Returns {"top3_names": [...], "rank_history": DataFrame, "rank_stats": DataFrame}.
    """
    if gw_history_df.empty:
        return {"top3_names": [], "rank_history": pd.DataFrame(), "rank_stats": pd.DataFrame()}

    last_gw_row = gw_history_df.iloc[-1]
    player_cols = [col for col in gw_history_df.columns if col != "GW"]
    final_standings = sorted(((p, last_gw_row[p]) for p in player_cols), key=lambda x: x[1], reverse=True)
    top3_names = [name for name, _ in final_standings[:3]]

    rank_data = []
    for gw_idx, row in gw_history_df.iterrows():
        gw = row["GW"]
        for player_name in player_cols:
            points = row[player_name]
            rank = (gw_history_df.iloc[gw_idx][player_cols] >= points).sum()
            rank_data.append({"GW": gw, "player_name": player_name, "points": points, "rank": rank})
    rank_history_df = pd.DataFrame(rank_data)

    stats_list = []
    for player in top3_names:
        player_ranks = rank_history_df[rank_history_df["player_name"] == player]
        if player_ranks.empty:
            continue
        stats_list.append(
            {
                "player_name": player,
                "avg_rank": player_ranks["rank"].mean(),
                "best_rank": player_ranks["rank"].min(),
                "worst_rank": player_ranks["rank"].max(),
                "weeks_at_rank1": (player_ranks["rank"] == 1).sum(),
                "weeks_in_top3": (player_ranks["rank"] <= 3).sum(),
            }
        )
    rank_stats_df = pd.DataFrame(stats_list)

    return {"top3_names": top3_names, "rank_history": rank_history_df, "rank_stats": rank_stats_df}


# ── GW team / pick data ──────────────────────────────────────────────────────────

def build_team_summary(
    picks_by_entry: dict[int, Optional[dict]],
    player_to_id: dict[int, str],
    player_to_price: dict[int, int],
    player_to_points: dict[int, int],
) -> pd.DataFrame:
    """Columns: player_name, own_count, captaincy_count, price, points."""
    records = []
    for picks_json in picks_by_entry.values():
        if not picks_json:
            continue
        for pick in picks_json.get("picks", []):
            pid = pick["element"]
            if pid not in player_to_id:
                continue
            records.append(
                {
                    "player_name": player_to_id[pid],
                    "player_price": player_to_price.get(pid, 0),
                    "player_points": player_to_points.get(pid, 0),
                    "is_captain": pick["is_captain"],
                }
            )

    if not records:
        return pd.DataFrame(columns=["player_name", "own_count", "captaincy_count", "price", "points"])

    df = pd.DataFrame(records)
    return (
        df.groupby("player_name")
        .agg(
            own_count=("player_name", "size"),
            captaincy_count=("is_captain", "sum"),
            price=("player_price", "first"),
            points=("player_points", "first"),
        )
        .reset_index()
    )


def get_active_chips(picks_by_entry: dict[int, Optional[dict]]) -> list[str]:
    return [
        picks_json["active_chip"]
        for picks_json in picks_by_entry.values()
        if picks_json and picks_json.get("active_chip")
    ]


def build_transfers(
    prev_picks_by_entry: dict[int, Optional[dict]],
    curr_picks_by_entry: dict[int, Optional[dict]],
    player_to_id: dict[int, str],
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Net squad changes between GW-1 and GW, per manager, aggregated by player."""
    empty_in = pd.DataFrame(columns=["player_name", "transfers_in"])
    empty_out = pd.DataFrame(columns=["player_name", "transfers_out"])

    transfers_in_ids: list[int] = []
    transfers_out_ids: list[int] = []

    for entry, curr_picks_json in curr_picks_by_entry.items():
        prev_picks_json = prev_picks_by_entry.get(entry)
        if not prev_picks_json or not curr_picks_json:
            continue
        prev_squad = {p["element"] for p in prev_picks_json.get("picks", [])}
        curr_squad = {p["element"] for p in curr_picks_json.get("picks", [])}
        if not prev_squad or not curr_squad:
            continue
        transfers_in_ids.extend(curr_squad - prev_squad)
        transfers_out_ids.extend(prev_squad - curr_squad)

    if not transfers_in_ids and not transfers_out_ids:
        return empty_in, empty_out

    def _aggregate(ids: list[int], col: str) -> pd.DataFrame:
        raw = pd.DataFrame({"player_id": ids})
        return (
            raw.assign(player_name=lambda d: d["player_id"].map(player_to_id))
            .dropna(subset=["player_name"])
            .groupby("player_name")
            .agg(**{col: ("player_name", "size")})
            .reset_index()
            .sort_values(col, ascending=False)
        )

    df_in = _aggregate(transfers_in_ids, "transfers_in") if transfers_in_ids else empty_in
    df_out = _aggregate(transfers_out_ids, "transfers_out") if transfers_out_ids else empty_out
    return df_in, df_out


def build_top3_detailed_stats(
    top3_names: list[str],
    entry_to_player: dict[int, str],
    curr_picks_by_entry: dict[int, Optional[dict]],
    prev_picks_by_entry: dict[int, Optional[dict]],
    histories_by_entry: dict[int, Optional[dict]],
    player_to_id: dict[int, str],
) -> dict:
    """Per-manager captain, starting XI, active chip, chips left, transfers made."""
    player_to_entry = {name: entry for entry, name in entry_to_player.items()}
    detailed_stats = {}

    for manager_name in top3_names:
        entry = player_to_entry.get(manager_name)
        picks_json = curr_picks_by_entry.get(entry) if entry is not None else None

        if not picks_json:
            detailed_stats[manager_name] = {
                "captain": "N/A",
                "starting_lineup": [],
                "active_chip": None,
                "chips_left": {},
                "transfers_made": 0,
            }
            continue

        picks = picks_json.get("picks", [])
        active_chip = picks_json.get("active_chip")

        captain_name = None
        starting_lineup = []
        for pick in picks:
            if pick.get("is_captain"):
                captain_name = player_to_id.get(pick["element"], f"Player {pick['element']}")
            if pick.get("position", 99) <= 11:
                starting_lineup.append(player_to_id.get(pick["element"], f"Player {pick['element']}"))

        chips_left = {}
        history_data = histories_by_entry.get(entry)
        if history_data and history_data.get("current"):
            latest_gw = max(history_data["current"], key=lambda x: x.get("event", 0))
            for chip in ("wildcard", "freehit", "bboost", "3xc"):
                chip_used = latest_gw.get(f"{chip}_used", 0)
                chips_left[chip] = 1 - chip_used if chip_used in (0, 1) else 0

        transfers_made = 0
        prev_picks_json = prev_picks_by_entry.get(entry) if entry is not None else None
        if prev_picks_json:
            prev_ids = {p["element"] for p in prev_picks_json.get("picks", [])}
            curr_ids = {p["element"] for p in picks}
            transfers_made = len(curr_ids - prev_ids)

        detailed_stats[manager_name] = {
            "captain": captain_name or "None",
            "starting_lineup": starting_lineup,
            "active_chip": active_chip,
            "chips_left": chips_left,
            "transfers_made": transfers_made,
        }

    return detailed_stats
