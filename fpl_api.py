"""
FPL API helpers — fetch and persist data from the Fantasy Premier League API.
"""

import json
import os
import statistics
from typing import Optional

import pandas as pd
import requests

FPL_BASE = "https://fantasy.premierleague.com/api"


# ── Player data ───────────────────────────────────────────────────────────────

def validate_gameweek_exists(gw: int) -> dict:
    """
    Validate that a gameweek exists in the current FPL season.

    Returns:
        The event metadata dict for the requested GW.

    Raises:
        ValueError if the GW is not part of the season schedule.
    """
    if isinstance(gw, bool) or not isinstance(gw, int):
        raise ValueError(
            f"GAMEWEEK must be an integer (e.g. 32). Got {gw!r} ({type(gw).__name__})."
        )

    response = requests.get(f"{FPL_BASE}/bootstrap-static/", timeout=30)
    response.raise_for_status()
    events = response.json().get("events", [])

    valid_ids = {event["id"] for event in events}
    if gw not in valid_ids:
        max_gw = max(valid_ids) if valid_ids else 38
        raise ValueError(
            f"GW{gw} does not exist for this season. Use a value from 1 to {max_gw}."
        )

    return next(event for event in events if event["id"] == gw)

def fetch_player_data(save_dir: str = "fpl_player_data") -> tuple[dict, dict, dict]:
    """
    Fetch global player info (name, price, points) from the bootstrap endpoint.

    Returns:
        player_to_id_mapping    {player_id -> web_name}
        player_to_price_mapping {player_id -> now_cost}
        player_to_points_mapping {player_id -> total_points}
    """
    response = requests.get(f"{FPL_BASE}/bootstrap-static/", timeout=30)
    response.raise_for_status()
    all_players = response.json()["elements"]

    player_to_id_mapping = {}
    player_to_price_mapping = {}
    player_to_points_mapping = {}

    for player in all_players:
        pid = player["id"]
        player_to_id_mapping[pid] = player["web_name"]
        player_to_price_mapping[pid] = player["now_cost"]
        player_to_points_mapping[pid] = player["total_points"]

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        _save_mapping_csv(
            player_to_id_mapping,
            f"{save_dir}/player_to_id_mapping.csv",
            "player_id",
            "player_name",
        )
        _save_mapping_csv(
            player_to_price_mapping,
            f"{save_dir}/player_to_price_mapping.csv",
            "player_id",
            "price",
        )
        _save_mapping_csv(
            player_to_points_mapping,
            f"{save_dir}/player_to_points_mapping.csv",
            "player_id",
            "points",
        )

    return player_to_id_mapping, player_to_price_mapping, player_to_points_mapping


def load_player_data(save_dir: str = "fpl_player_data") -> tuple[dict, dict, dict]:
    player_to_id = _load_mapping_csv(
        f"{save_dir}/player_to_id_mapping.csv",
        "player_id",
        "player_name",
        key_cast=int,
        value_cast=str,
    )
    player_to_price = _load_mapping_csv(
        f"{save_dir}/player_to_price_mapping.csv",
        "player_id",
        "price",
        key_cast=int,
        value_cast=int,
    )
    player_to_points = _load_mapping_csv(
        f"{save_dir}/player_to_points_mapping.csv",
        "player_id",
        "points",
        key_cast=int,
        value_cast=int,
    )
    return player_to_id, player_to_price, player_to_points


# ── League data ───────────────────────────────────────────────────────────────

def save_league_data(league_id: str) -> None:
    """Fetch league standings and save as JSON."""
    save_dir = f"league_{league_id}/league_data"
    os.makedirs(save_dir, exist_ok=True)

    response = requests.get(f"{FPL_BASE}/leagues-classic/{league_id}/standings/", timeout=30)
    response.raise_for_status()
    data = response.json()

    file_path = f"{save_dir}/league_{league_id}_data.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    print(f"League data saved to {file_path}")


def get_entry_to_player_mapping(league_id: str) -> dict:
    """
    Parse the saved league JSON to build an {entry_id -> player_name} dict,
    persist it as a CSV, and return it.
    """
    with open(f"league_{league_id}/league_data/league_{league_id}_data.json", encoding="utf-8") as f:
        data = json.load(f)

    # Before GW1 results live in new_entries; after that in standings
    results = data["new_entries"]["results"]
    if results:
        entry_to_player = {
            r["entry"]: f"{r['player_first_name']} {r['player_last_name']}"
            for r in results
        }
    else:
        results = data["standings"]["results"]
        entry_to_player = {r["entry"]: r["player_name"] for r in results}

    print("Entry → Player mapping:", entry_to_player)

    csv_path = f"league_{league_id}/league_data/league_{league_id}_entry_to_player_mapping.csv"
    _save_mapping_csv(entry_to_player, csv_path, "entry_id", "player_name")
    print(f"Mapping saved to {csv_path}")
    return entry_to_player


def load_entry_to_player_mapping(league_id: str) -> dict:
    return _load_mapping_csv(
        f"league_{league_id}/league_data/league_{league_id}_entry_to_player_mapping.csv",
        "entry_id",
        "player_name",
        key_cast=int,
        value_cast=str,
    )


# ── User / history data ───────────────────────────────────────────────────────

def fetch_and_save_history(league_id: str, entry_to_player: dict) -> None:
    """Download per-user season history JSON files."""
    save_dir = f"league_{league_id}/user_data"
    os.makedirs(save_dir, exist_ok=True)

    for entry, player_name in entry_to_player.items():
        response = requests.get(f"{FPL_BASE}/entry/{entry}/history/", timeout=30)
        if response.status_code == 200:
            file_path = f"{save_dir}/{player_name.replace(' ', '_')}_{entry}_history.json"
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(response.json(), f, indent=4)
            print(f"Saved history for {player_name}")
        else:
            print(f"Failed to fetch history for {player_name} (HTTP {response.status_code})")


def build_gw_history_df(league_id: str, entry_to_player: dict) -> pd.DataFrame:
    """
    Build a cumulative-points-per-GW DataFrame from saved history files
    and persist it as a CSV.

    Columns: GW, <player_name>, ...
    """
    user_data_dir = f"league_{league_id}/user_data"

    # Determine how many GWs have been played (mode across all users)
    n_gws_list = []
    for entry, player_name in entry_to_player.items():
        path = f"{user_data_dir}/{player_name.replace(' ', '_')}_{entry}_history.json"
        with open(path, encoding="utf-8") as f:
            n_gws_list.append(len(json.load(f)["current"]))
    n_gws = statistics.mode(n_gws_list)

    gw_history_df = pd.DataFrame({"GW": [f"GW{gw}" for gw in range(1, n_gws + 1)]})

    for entry, player_name in entry_to_player.items():
        path = f"{user_data_dir}/{player_name.replace(' ', '_')}_{entry}_history.json"
        with open(path, encoding="utf-8") as f:
            history = json.load(f)["current"]

        cumulative = 0
        cum_points = []
        for game in history:
            cumulative += game["points"]
            cum_points.append(cumulative)

        gw_history_df[player_name] = cum_points

    csv_path = f"league_{league_id}/league_data/league_{league_id}_gw_history_df.csv"
    gw_history_df.to_csv(csv_path, index=False)
    print(f"GW history saved to {csv_path}")
    return gw_history_df


# ── GW team / pick data ───────────────────────────────────────────────────────

def get_gw_team_summary(
    user_ids: list,
    gw: int,
    player_to_id: dict,
    player_to_price: dict,
    player_to_points: dict,
    save_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    Fetch each user's GW picks and return a summary DataFrame.

    Columns: player_name, own_count, captaincy_count, price, points
    """
    records = []
    for user_id in user_ids:
        response = requests.get(f"{FPL_BASE}/entry/{user_id}/event/{gw}/picks/", timeout=30)
        if response.status_code != 200:
            continue
        for pick in response.json()["picks"]:
            pid = pick["element"]
            records.append(
                {
                    "player_name": player_to_id[pid],
                    "player_price": player_to_price[pid],
                    "player_points": player_to_points[pid],
                    "is_captain": pick["is_captain"],
                }
            )

    if not records:
        return pd.DataFrame(
            columns=["player_name", "own_count", "captaincy_count", "price", "points"]
        )

    df = pd.DataFrame(records)
    df_summary = (
        df.groupby("player_name")
        .agg(
            own_count=("player_name", "size"),
            captaincy_count=("is_captain", "sum"),
            price=("player_price", "first"),
            points=("player_points", "first"),
        )
        .reset_index()
    )

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        df_summary.to_csv(f"{save_dir}/team_summary_GW{gw}.csv", index=False)

    return df_summary


def get_active_chips(user_ids: list, gw: int) -> list[str]:
    """Return a list of active chip names (one per user who played a chip)."""
    chips = []
    for user_id in user_ids:
        response = requests.get(f"{FPL_BASE}/entry/{user_id}/event/{gw}/picks/", timeout=30)
        if response.status_code == 200:
            chip = response.json().get("active_chip")
            if chip:
                chips.append(chip)
    return chips


def get_transfers_df(
    user_ids: list,
    gw: int,
    player_to_id: dict,
    save_dir: Optional[str] = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Infer transfers for the given GW by comparing each manager's squad
    between GW-1 and GW.

    This tracks net squad changes and avoids over-counting churn from
    repeated in/out moves within the same GW (e.g., wildcard tinkering).

    Returns:
        df_in  — transfers in,  columns: player_name, transfers_in
        df_out — transfers out, columns: player_name, transfers_out
    """
    empty_in = pd.DataFrame(columns=["player_name", "transfers_in"])
    empty_out = pd.DataFrame(columns=["player_name", "transfers_out"])

    if gw <= 1:
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            empty_in.to_csv(f"{save_dir}/transfers_in_GW{gw}.csv", index=False)
            empty_out.to_csv(f"{save_dir}/transfers_out_GW{gw}.csv", index=False)
        return empty_in, empty_out

    transfers_in_ids = []
    transfers_out_ids = []

    for user_id in user_ids:
        prev_response = requests.get(f"{FPL_BASE}/entry/{user_id}/event/{gw - 1}/picks/", timeout=30)
        curr_response = requests.get(f"{FPL_BASE}/entry/{user_id}/event/{gw}/picks/", timeout=30)

        if prev_response.status_code != 200 or curr_response.status_code != 200:
            continue

        prev_squad = {pick["element"] for pick in prev_response.json().get("picks", [])}
        curr_squad = {pick["element"] for pick in curr_response.json().get("picks", [])}

        if not prev_squad or not curr_squad:
            continue

        transfers_in_ids.extend(curr_squad - prev_squad)
        transfers_out_ids.extend(prev_squad - curr_squad)

    if not transfers_in_ids and not transfers_out_ids:
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
            empty_in.to_csv(f"{save_dir}/transfers_in_GW{gw}.csv", index=False)
            empty_out.to_csv(f"{save_dir}/transfers_out_GW{gw}.csv", index=False)
        return empty_in, empty_out

    df_in_raw = pd.DataFrame({"player_id": transfers_in_ids})
    df_out_raw = pd.DataFrame({"player_id": transfers_out_ids})

    df_in = (
        df_in_raw
        .assign(player_name=lambda d: d["player_id"].map(player_to_id))
        .dropna(subset=["player_name"])
        .groupby("player_name")
        .agg(transfers_in=("player_name", "size"))
        .reset_index()
        .sort_values("transfers_in", ascending=False)
    )

    df_out = (
        df_out_raw
        .assign(player_name=lambda d: d["player_id"].map(player_to_id))
        .dropna(subset=["player_name"])
        .groupby("player_name")
        .agg(transfers_out=("player_name", "size"))
        .reset_index()
        .sort_values("transfers_out", ascending=False)
    )

    if save_dir:
        os.makedirs(save_dir, exist_ok=True)
        df_in.to_csv(f"{save_dir}/transfers_in_GW{gw}.csv", index=False)
        df_out.to_csv(f"{save_dir}/transfers_out_GW{gw}.csv", index=False)

    return df_in, df_out


# ── Top 3 Leaders Analysis ────────────────────────────────────────────────────

def get_previous_gw_standings(league_id: str, entry_to_player: dict) -> pd.DataFrame:
    """
    Fetch current league standings from FPL API and map to player names.
    
    These standings reflect the rankings at the time of the API call,
    which is typically the previous GW when analyzing a current GW.

    Args:
        league_id: The league ID
        entry_to_player: {entry_id -> player_name} mapping dict

    Returns:
        DataFrame with columns: player_name, rank, total_points (sorted by rank)
    """
    response = requests.get(f"{FPL_BASE}/leagues-classic/{league_id}/standings/", timeout=30)
    response.raise_for_status()
    data = response.json()

    results = data.get("standings", {}).get("results", [])
    if not results:
        return pd.DataFrame(columns=["player_name", "rank", "total_points"])

    standings_list = []
    for result in results:
        entry = result["entry"]
        standings_list.append(
            {
                "player_name": entry_to_player.get(entry, "Unknown"),
                "rank": result.get("rank", result.get("entry_rank", None)),
                "total_points": result.get("total", result.get("event_total", 0)),
            }
        )

    df = pd.DataFrame(standings_list).sort_values("rank").reset_index(drop=True)
    return df


def get_standings_for_gw(gw_history_df: pd.DataFrame, gw: int) -> pd.DataFrame:
    """
    Build standings table from GW history data for a specific gameweek.

    Args:
        gw_history_df: DataFrame with GW column and player names as columns
        gw: Gameweek number to get standings for

    Returns:
        DataFrame with columns: player_name, rank, total_points (sorted by rank)
    """
    gw_col = f"GW{gw}"
    
    if gw_col not in gw_history_df.columns:
        return pd.DataFrame(columns=["player_name", "rank", "total_points"])
    
    standings_list = []
    for player_name in gw_history_df.columns:
        if player_name == "GW":
            continue
        points = gw_history_df[gw_history_df["GW"] == gw_col][player_name].values
        if len(points) > 0:
            standings_list.append(
                {
                    "player_name": player_name,
                    "total_points": int(points[0]),
                }
            )
    
    df = pd.DataFrame(standings_list).sort_values("total_points", ascending=False).reset_index(drop=True)
    df["rank"] = range(1, len(df) + 1)
    return df[["player_name", "rank", "total_points"]]


def get_top3_ranking_history(gw_history_df: pd.DataFrame) -> dict:
    """
    Analyze top 3 managers' rank history across all gameweeks.

    Args:
        gw_history_df: DataFrame with GW column and player names as columns (from build_gw_history_df).

    Returns:
        dict with keys:
            "top3_names": list of top 3 player names (final standings)
            "rank_history": DataFrame with columns [GW, player_name, rank, weeks_at_rank1, weeks_in_top3]
            "rank_stats": DataFrame with aggregated stats per player
    """
    # Get final top 3 from most recent GW
    last_gw_row = gw_history_df.iloc[-1]
    
    player_cols = [col for col in gw_history_df.columns if col != "GW"]
    final_standings = [(player, last_gw_row[player]) for player in player_cols]
    final_standings.sort(key=lambda x: x[1], reverse=True)
    top3_names = [name for name, _ in final_standings[:3]]

    rank_data = []
    for gw_idx, row in gw_history_df.iterrows():
        gw = row["GW"]

        for player_name in player_cols:
            points = row[player_name]
            rank = (gw_history_df.iloc[gw_idx][player_cols] >= points).sum()

            rank_data.append(
                {
                    "GW": gw,
                    "player_name": player_name,
                    "points": points,
                    "rank": rank,
                }
            )

    rank_history_df = pd.DataFrame(rank_data)

    stats_list = []
    for player in top3_names:
        player_ranks = rank_history_df[rank_history_df["player_name"] == player]
        if player_ranks.empty:
            continue

        weeks_at_rank1 = (player_ranks["rank"] == 1).sum()
        weeks_in_top3 = (player_ranks["rank"] <= 3).sum()
        avg_rank = player_ranks["rank"].mean()
        best_rank = player_ranks["rank"].min()
        worst_rank = player_ranks["rank"].max()

        stats_list.append(
            {
                "player_name": player,
                "avg_rank": avg_rank,
                "best_rank": best_rank,
                "worst_rank": worst_rank,
                "weeks_at_rank1": weeks_at_rank1,
                "weeks_in_top3": weeks_in_top3,
            }
        )

    rank_stats_df = pd.DataFrame(stats_list)

    return {
        "top3_names": top3_names,
        "rank_history": rank_history_df,
        "rank_stats": rank_stats_df,
    }


def get_top3_detailed_stats(
    user_ids: list,
    entry_to_player: dict,
    gw: int,
    player_to_id: dict,
) -> dict:
    """
    Fetch detailed GW stats for each user: captain, starting XI names, active chip, chips left, transfers.

    Args:
        user_ids: List of entry/user IDs
        entry_to_player: {entry_id -> player_name} mapping
        gw: Gameweek number
        player_to_id: {player_id -> player_name} mapping

    Returns:
        dict keyed by player_name with values containing:
        captain, starting_lineup, active_chip, chips_left, transfers_made
    """
    detailed_stats = {}

    for user_id in user_ids:
        manager_name = entry_to_player.get(user_id, f"Entry {user_id}")
        
        # Fetch picks for this GW
        response = requests.get(f"{FPL_BASE}/entry/{user_id}/event/{gw}/picks/", timeout=30)
        if response.status_code != 200:
            detailed_stats[manager_name] = {
                "captain": "N/A",
                "starting_lineup": [],
                "active_chip": None,
                "chips_left": {},
                "transfers_made": 0,
            }
            continue

        picks_data = response.json()
        picks = picks_data.get("picks", [])
        active_chip = picks_data.get("active_chip")

        # Find captain
        captain_name = None
        starting_lineup = []
        for pick in picks:
            if pick.get("is_captain"):
                captain_id = pick["element"]
                captain_name = player_to_id.get(captain_id, f"Player {captain_id}")
            if pick.get("position") <= 11:
                starting_lineup.append(player_to_id.get(pick["element"], f"Player {pick['element']}"))

        # Fetch entry history to get chips remaining
        chips_left = {}
        history_response = requests.get(f"{FPL_BASE}/entry/{user_id}/history/", timeout=30)
        if history_response.status_code == 200:
            history_data = history_response.json()
            current_season = history_data.get("current", [])
            if current_season:
                latest_gw = max(current_season, key=lambda x: x.get("event", 0))
                available_chips = ["wildcard", "freehit", "bboost", "3xc"]
                for chip in available_chips:
                    chip_used = latest_gw.get(f"{chip}_used", 0)
                    chips_left[chip] = 1 - chip_used if chip_used in [0, 1] else 0

        # Get transfers made for this GW
        transfers_made = 0
        if gw > 1:
            prev_response = requests.get(f"{FPL_BASE}/entry/{user_id}/event/{gw - 1}/picks/", timeout=30)
            if prev_response.status_code == 200:
                prev_picks = {p["element"] for p in prev_response.json().get("picks", [])}
                curr_picks = {p["element"] for p in picks}
                transfers_made = len(curr_picks - prev_picks)

        detailed_stats[manager_name] = {
            "captain": captain_name or "None",
            "starting_lineup": starting_lineup,
            "active_chip": active_chip,
            "chips_left": chips_left,
            "transfers_made": transfers_made,
        }

    return detailed_stats


# ── Internal helpers ──────────────────────────────────────────────────────────

def _save_mapping_csv(mapping: dict, path: str, key_col: str, value_col: str) -> None:
    pd.DataFrame({key_col: list(mapping.keys()), value_col: list(mapping.values())}).to_csv(
        path,
        index=False,
    )


def _load_mapping_csv(
    path: str,
    key_col: str,
    value_col: str,
    key_cast=None,
    value_cast=None,
) -> dict:
    df = pd.read_csv(path)
    keys = df[key_col]
    values = df[value_col]

    if key_cast is not None:
        keys = keys.map(key_cast)
    if value_cast is not None:
        values = values.map(value_cast)

    return dict(zip(keys, values))
