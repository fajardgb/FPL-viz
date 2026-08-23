"""
Visualization helpers for the FPL league analysis.
"""

import os
from typing import Optional

import matplotlib.pyplot as plt
import pandas as pd


def _save(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    plt.savefig(path)


def _add_bar_labels(bars, fmt=int, y_offset=0.1, ax=None) -> None:
    text_func = ax.text if ax is not None else plt.text
    for bar in bars:
        yval = bar.get_height()
        text_func(
            bar.get_x() + bar.get_width() / 2,
            yval + y_offset,
            fmt(yval),
            ha="center",
            va="bottom",
            fontsize=10,
        )


# ── Active chips ──────────────────────────────────────────────────────────────

def plot_active_chips(chips: list[str], gw: int, save_dir: Optional[str] = None) -> None:
    unique = list(set(chips))
    counts = [chips.count(c) for c in unique]

    plt.figure(figsize=(4, 2))
    plt.bar(unique, counts)
    plt.xlabel("Chips")
    plt.ylabel("Count")
    plt.title(f"Active Chips for GW{gw}")
    _add_bar_labels(plt.bar(unique, counts), y_offset=0.05)
    plt.tight_layout()

    if save_dir:
        _save(f"{save_dir}/active_chips_GW{gw}.png")
    plt.close()


# ── Captaincy ─────────────────────────────────────────────────────────────────

def plot_captaincy(team_df: pd.DataFrame, gw: int, save_dir: Optional[str] = None) -> None:
    sorted_df = (
        team_df[team_df["captaincy_count"] > 0]
        .sort_values("captaincy_count", ascending=False)
    )

    plt.figure(figsize=(8, 6))
    bars = plt.bar(sorted_df["player_name"], sorted_df["captaincy_count"], color="royalblue")
    plt.xlabel("Captains")
    plt.ylabel("Count")
    plt.title(f"Captains for GW{gw}")
    plt.xticks(rotation=30)
    _add_bar_labels(bars)
    plt.tight_layout()

    if save_dir:
        _save(f"{save_dir}/captaincy_GW{gw}.png")
    plt.close()


# ── Most owned ────────────────────────────────────────────────────────────────

def plot_most_owned(
    team_df: pd.DataFrame, gw: int, n: int = 20, save_dir: Optional[str] = None
) -> None:
    top_df = team_df.sort_values("own_count", ascending=False).head(n)

    plt.figure(figsize=(10, 6))
    bars = plt.bar(top_df["player_name"], top_df["own_count"], color="skyblue", edgecolor="grey")
    plt.xlabel("Player")
    plt.ylabel("Own Count")
    plt.title(f"Top {n} Most Owned Players for GW{gw}")
    plt.xticks(rotation=45)
    _add_bar_labels(bars)
    plt.tight_layout()

    if save_dir:
        _save(f"{save_dir}/most_owned_GW{gw}.png")
    plt.close()


# ── Differentials ─────────────────────────────────────────────────────────────

def _price_label(yval: float) -> str:
    """Convert raw FPL price (e.g. 55) to display string (e.g. '5.5')."""
    s = str(int(yval))
    return s[:-1] + "." + s[-1]


def plot_differentials_by_price(
    team_df: pd.DataFrame,
    gw: int,
    own_max: int,
    top_n: int = 10,
    save_dir: Optional[str] = None,
) -> None:
    diff_df = (
        team_df[team_df["own_count"] <= own_max]
        .sort_values("price", ascending=False)
        .head(top_n)
    )

    plt.figure(figsize=(10, 6))
    bars = plt.bar(diff_df["player_name"], diff_df["price"], color="pink", edgecolor="grey")
    plt.xlabel("Player")
    plt.ylabel("Price")
    plt.title(f"Top {top_n} Differentials by Price — GW{gw}")
    plt.xticks(rotation=30)
    _add_bar_labels(bars, fmt=_price_label, y_offset=0.2)
    plt.tight_layout()

    if save_dir:
        _save(f"{save_dir}/differentials_by_price_GW{gw}.png")
    plt.close()


def plot_differentials_by_points(
    team_df: pd.DataFrame,
    gw: int,
    own_max: int,
    top_n: int = 10,
    save_dir: Optional[str] = None,
) -> None:
    diff_df = (
        team_df[team_df["own_count"] <= own_max]
        .sort_values("points", ascending=False)
        .head(top_n)
    )

    plt.figure(figsize=(10, 6))
    bars = plt.bar(diff_df["player_name"], diff_df["points"], color="rebeccapurple", edgecolor="grey")
    plt.xlabel("Player")
    plt.ylabel("Points")
    plt.title(f"Top {top_n} Differentials by Points — GW{gw}")
    plt.xticks(rotation=30)
    _add_bar_labels(bars, y_offset=0.2)
    plt.tight_layout()

    if save_dir:
        _save(f"{save_dir}/differentials_by_points_GW{gw}.png")
    plt.close()


# ── Transfers ─────────────────────────────────────────────────────────────────

def plot_transfers(
    df_in: pd.DataFrame,
    df_out: pd.DataFrame,
    gw: int,
    save_dir: Optional[str] = None,
) -> None:
    # Transfers in
    plt.figure(figsize=(10, 6))
    bars = plt.bar(df_in["player_name"], df_in["transfers_in"], color="seagreen", edgecolor="grey")
    plt.xlabel("Player")
    plt.ylabel("Transfers In")
    plt.title(f"Transfers In for GW{gw}")
    plt.xticks(rotation=55)
    _add_bar_labels(bars, y_offset=0.05)
    plt.tight_layout()
    if save_dir:
        _save(f"{save_dir}/transfers_in_GW{gw}.png")
    plt.close()

    # Transfers out
    plt.figure(figsize=(10, 6))
    bars = plt.bar(df_out["player_name"], df_out["transfers_out"], color="crimson", edgecolor="grey")
    plt.xlabel("Player")
    plt.ylabel("Transfers Out")
    plt.title(f"Transfers Out for GW{gw}")
    plt.xticks(rotation=55)
    _add_bar_labels(bars, y_offset=0.05)
    plt.tight_layout()
    if save_dir:
        _save(f"{save_dir}/transfers_out_GW{gw}.png")
    plt.close()


# ── Top 3 Leaders ─────────────────────────────────────────────────────────────

def plot_top3_current_standings(
    standings_df: pd.DataFrame,
    save_dir: Optional[str] = None,
) -> None:
    """
    Plot all league standings with rank-based medal colors.

    1st place: Gold, 2nd place: Silver, 3rd place: Bronze, Rest: White with black edge.

    Args:
        standings_df: Either:
            1) DataFrame with columns [rank, player_name, total_points], or
            2) One-row DataFrame where manager names are columns and values are points
               (optionally with a "GW" column).
    """
    if standings_df.empty:
        return

    if {"rank", "player_name", "total_points"}.issubset(standings_df.columns):
        plot_df = standings_df[["player_name", "rank", "total_points"]].copy()
    else:
        # Convert one-row wide format (manager columns) to long standings format.
        first_row = standings_df.iloc[0].copy()
        if "GW" in first_row.index:
            first_row = first_row.drop(labels=["GW"])

        points_series = pd.to_numeric(first_row, errors="coerce").dropna()
        plot_df = (
            points_series
            .sort_values(ascending=False)
            .rename_axis("player_name")
            .reset_index(name="total_points")
        )
        plot_df["rank"] = range(1, len(plot_df) + 1)
        plot_df = plot_df[["player_name", "rank", "total_points"]]

    if plot_df.empty:
        return

    rank_colors = {1: "gold", 2: "silver", 3: "#CD7F32"}
    colors = [rank_colors.get(rank, "white") for rank in plot_df["rank"]]

    plt.figure(figsize=(12, max(8, len(plot_df) * 0.3)))
    bars = plt.barh(
        plot_df["player_name"],
        plot_df["total_points"],
        color=colors,
        edgecolor="black",
        linewidth=1.5,
    )
    plt.xlabel("Total Points", fontsize=11)
    plt.ylabel("Manager", fontsize=11)
    plt.title("League Standings", fontsize=13, fontweight="bold")

    # Add point value labels (bold if top-3)
    for bar, rank, points in zip(bars, plot_df["rank"], plot_df["total_points"]):
        label_text = f"{int(points)}pts"
        plt.text(
            bar.get_width() + 5,
            bar.get_y() + bar.get_height() / 2,
            label_text,
            va="center",
            fontweight="bold" if rank <= 3 else "normal",
        )

    plt.tight_layout()
    if save_dir:
        _save(f"{save_dir}/top3_current_standings.png")
    plt.close()


def plot_top3_rank_history(
    rank_history_df: pd.DataFrame,
    top3_names: list[str],
    save_dir: Optional[str] = None,
) -> None:
    """
    Plot rank trajectory across gameweeks for top 3 managers.

    Args:
        rank_history_df: DataFrame with columns [GW, player_name, rank]
        top3_names: List of top 3 player names to highlight
    """

    colors = ["gold", "silver", "#CD7F32"]
    markers = ["o", "s", "^"]

    plt.figure(figsize=(12, 6))
    
    for i, player_name in enumerate(top3_names):
        player_data = rank_history_df[rank_history_df["player_name"] == player_name]
        if not player_data.empty:
            gw_nums = [int(gw.replace("GW", "")) for gw in player_data["GW"]]
            plt.plot(
                gw_nums,
                player_data["rank"],
                label=player_name,
                marker=markers[i],
                linewidth=2.5,
                markersize=8,
                color=colors[i],
            )

    plt.xlabel("Gameweek")
    plt.ylabel("Rank")
    plt.title("Top 3 Managers: Rank Progression Across Season")
    plt.gca().invert_yaxis()
    plt.legend(loc="best")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    
    if save_dir:
        _save(f"{save_dir}/top3_rank_history.png")
    plt.close()


def plot_top3_stats(
    rank_stats_df: pd.DataFrame,
    save_dir: Optional[str] = None,
) -> None:
    """
    Plot summary stats for top 3: weeks at #1, weeks in top 3.

    Args:
        rank_stats_df: DataFrame with columns [player_name, weeks_at_rank1, weeks_in_top3]
    """
    if rank_stats_df.empty:
        return

    _, axes = plt.subplots(1, 2, figsize=(15, 5))
    
    # Weeks at Rank 1
    ax = axes[0]
    bars = ax.bar(rank_stats_df["player_name"], rank_stats_df["weeks_at_rank1"], color="gold")
    ax.set_ylabel("Weeks")
    ax.set_title("Weeks at Rank #1")
    ax.set_ylim(0, rank_stats_df["weeks_at_rank1"].max() + 2)
    _add_bar_labels(bars, y_offset=0.2, ax=ax)

    # Weeks in Top 3
    ax = axes[1]
    bars = ax.bar(rank_stats_df["player_name"], rank_stats_df["weeks_in_top3"], color="silver")
    ax.set_ylabel("Weeks")
    ax.set_title("Weeks in Top 3")
    ax.set_ylim(0, rank_stats_df["weeks_in_top3"].max() + 2)
    _add_bar_labels(bars, y_offset=0.2, ax=ax)

    plt.tight_layout()
    if save_dir:
        _save(f"{save_dir}/top3_stats.png")
    plt.close()


def plot_top3_detailed_stats(
    top3_names: list[str],
    detailed_stats: dict,
    save_dir: Optional[str] = None,
) -> None:
    """
    Display detailed GW stats for top 3 managers in card format.

    Args:
        top3_names: List of top 3 player names
        detailed_stats: Dict keyed by player_name with stats
        save_dir: Optional directory to save the plot
    """
    if not top3_names or not detailed_stats:
        return

    _, axes = plt.subplots(1, 3, figsize=(16, 6))
    if len(top3_names) == 1:
        axes = [axes]
    
    medal_colors = ["gold", "silver", "#CD7F32"]
    
    for idx, (ax, manager_name) in enumerate(zip(axes, top3_names)):
        ax.axis("off")
        stats = detailed_stats.get(manager_name, {})
        
        # Medal emojis
        medals = ["1st", "2nd", "3rd"]
        medal = medals[idx] if idx < 3 else ""
        
        # Build text content
        text_content = f"{medal} {manager_name}\n"
        text_content += "─" * 30 + "\n\n"
        text_content += f"Captain:  {stats.get('captain', 'N/A')}\n"
        starting_lineup = stats.get("starting_lineup", [])
        text_content += "Starting XI:\n"
        if starting_lineup:
            for i in range(0, len(starting_lineup), 3):
                text_content += "  " + ", ".join(starting_lineup[i:i + 3]) + "\n"
        else:
            text_content += "  N/A\n"
        
        active_chip = stats.get("active_chip")
        chip_text = active_chip.upper() if active_chip else "None"
        text_content += f"\nActive Chip:  {chip_text}\n"
        
        # Build chips remaining display
        chips_left = stats.get("chips_left", {})
        chip_names = {"wildcard": "WC", "freehit": "FH", "bboost": "BB", "3xc": "3xC"}
        chips_summary = ", ".join(f"{chip_names.get(chip, chip)}" for chip, remaining in chips_left.items() if remaining)
        text_content += f"Chips Left:  {chips_summary or 'None'}\n"
        
        text_content += f"Transfers:  {stats.get('transfers_made', 0)}\n"
        
        # Display text in box
        ax.text(
            0.5, 0.5, text_content,
            transform=ax.transAxes,
            fontsize=9,
            verticalalignment="center",
            horizontalalignment="center",
            family="monospace",
            bbox=dict(boxstyle="round", facecolor=medal_colors[idx], alpha=0.3, edgecolor="black", linewidth=2, pad=1)
        )
    
    plt.tight_layout()
    if save_dir:
        _save(f"{save_dir}/top3_detailed_stats.png")
    plt.close()
