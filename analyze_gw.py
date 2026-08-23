"""
analyze_gw.py — Run each gameweek to generate charts and summaries.

Steps:
  1. Fetch fresh global player data (name / price / points)
  2. Load the league's entry → player mapping
  3. Fetch GW team picks → summary DataFrame + CSV
  4. Plot: active chips, captaincy, most owned, differentials, transfers
  5. Analyze top 3 leaders: current standings, rank history, tenure at #1 and top 3
"""
import config
import fpl_api
import plots


def main():
    league_id = config.LEAGUE_ID
    gw = config.GAMEWEEK
    save_dir = f"league_{league_id}/output/GW{gw}"

    print(f"=== Analysing GW{gw} for league {league_id} ===\n")

    # Validate GW before doing any expensive requests/plotting.
    try:
        event_info = fpl_api.validate_gameweek_exists(gw)
    except ValueError as exc:
        print(f"Invalid GAMEWEEK in config.py: {exc}")
        return

    if event_info.get("is_next"):
        print(f"GW{gw} exists but has not started yet. Picks may be unavailable until the deadline.")

    # 1. Player data
    print("Fetching player data from FPL API...")
    player_to_id, player_to_price, player_to_points = fpl_api.fetch_player_data(
        save_dir=config.FPL_PLAYER_DATA_DIR
    )

    # 2. League membership
    entry_to_player = fpl_api.load_entry_to_player_mapping(league_id)
    user_ids = list(entry_to_player.keys())
    print(f"League has {len(user_ids)} managers.\n")

    # 3. TOP 3 LEADERS ANALYSIS (Option A: history-based)
    print("Analyzing top 3 leaders...")
    print("Fetching and saving user history...")
    fpl_api.fetch_and_save_history(league_id, entry_to_player)

    print("Building GW history DataFrame...")
    gw_history_df = fpl_api.build_gw_history_df(league_id, entry_to_player)

    # keep only row of previous GW
    gw_history_df = gw_history_df[gw_history_df["GW"] != f"GW{gw}"]  # filter out current GW if present
    prev_gw_df = gw_history_df[gw_history_df["GW"] == f"GW{gw - 1}"]
    prev_gw_points = prev_gw_df.iloc[0].drop(labels=["GW"])
    top3_names = (
        prev_gw_points.sort_values(ascending=False)
        .head(3)
        .index
        .tolist()
    )
    print(f"Using GW{gw - 1} history for top-3 plot.") 
    print(f"Top 3: {', '.join(top3_names)}\n")
    plots.plot_top3_current_standings(prev_gw_df, save_dir=save_dir)

    # Build rank history and stats from full GW history
    top3_analysis = fpl_api.get_top3_ranking_history(gw_history_df)
    plots.plot_top3_rank_history(top3_analysis["rank_history"], top3_analysis["top3_names"], save_dir=save_dir)
    plots.plot_top3_stats(top3_analysis["rank_stats"], save_dir=save_dir)

    print("\nTop 3 Rank Stats:")
    print(top3_analysis["rank_stats"].to_string(index=False))
    print()

    # Fetch and plot detailed GW stats for top 3
    print("Fetching detailed GW stats for top 3...")
    detailed_stats = fpl_api.get_top3_detailed_stats(
        user_ids=user_ids,
        entry_to_player=entry_to_player,
        gw=gw,
        player_to_id=player_to_id,
    )
    plots.plot_top3_detailed_stats(top3_analysis["top3_names"], detailed_stats, save_dir=save_dir)
    print()

    # 4. GW team summary
    print("Fetching GW picks...")
    team_df = fpl_api.get_gw_team_summary(
        user_ids=user_ids,
        gw=gw,
        player_to_id=player_to_id,
        player_to_price=player_to_price,
        player_to_points=player_to_points,
        save_dir=save_dir,
    )
    if team_df.empty:
        print(
            f"No team data found for GW{gw}. This usually means picks are not available yet for that GW."
        )
        return

    # 5. Active chips
    print("Fetching active chips...")
    chips = fpl_api.get_active_chips(user_ids, gw)
    if chips:
        plots.plot_active_chips(chips, gw, save_dir=save_dir)
    else:
        print("No chips played this GW.")

    # 6. Captaincy
    plots.plot_captaincy(team_df, gw, save_dir=save_dir)

    # 7. Most owned
    plots.plot_most_owned(team_df, gw, n=config.N_MOST_OWNED, save_dir=save_dir)

    # 8. Differentials
    own_max = int(len(user_ids) * config.DIFFERENTIAL_OWNERSHIP_THRESHOLD)
    print(f"\nDifferential threshold: owned by ≤ {own_max} managers ({config.DIFFERENTIAL_OWNERSHIP_THRESHOLD:.0%})")
    plots.plot_differentials_by_price(team_df, gw, own_max, top_n=config.N_DIFFERENTIALS, save_dir=save_dir)
    plots.plot_differentials_by_points(team_df, gw, own_max, top_n=config.N_DIFFERENTIALS, save_dir=save_dir)

    # 9. Transfers
    print("\nFetching transfers...")
    df_in, df_out = fpl_api.get_transfers_df(
        user_ids=user_ids,
        gw=gw,
        player_to_id=player_to_id,
        save_dir=save_dir,
    )
    if not df_in.empty or not df_out.empty:
        plots.plot_transfers(df_in, df_out, gw, save_dir=save_dir)
    else:
        print("No transfers recorded for this GW.")

    print(f"\nDone! Output saved to {save_dir}/")


if __name__ == "__main__":
    main()
