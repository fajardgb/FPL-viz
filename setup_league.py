"""
setup_league.py — Run once at the start of the season (or when adding a new league).

Steps:
  1. Fetch and save league standings JSON
  2. Build the entry → player-name mapping (CSV)
  3. Download per-user history JSONs
  4. Build the cumulative GW history DataFrame (CSV)
"""

import config
import fpl_api


def main():
    league_id = config.LEAGUE_ID

    print(f"=== Setting up league {league_id} ===\n")

    # 1. Fetch league standings
    print("Fetching league data...")
    fpl_api.save_league_data(league_id)

    # 2. Build entry → player mapping
    print("\nBuilding entry → player mapping...")
    entry_to_player = fpl_api.get_entry_to_player_mapping(league_id)

    # 3. Download per-user history
    print("\nFetching user histories...")
    fpl_api.fetch_and_save_history(league_id, entry_to_player)

    # 4. Build GW history DataFrame
    print("\nBuilding GW history DataFrame...")
    fpl_api.build_gw_history_df(league_id, entry_to_player)

    print("\nDone! League setup complete.")


if __name__ == "__main__":
    main()
