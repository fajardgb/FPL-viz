"""
report.py — orchestrates a single GW report: validate -> cache-check -> fetch
(if missing) -> analyze -> render charts. This is the async replacement for
the old analyze_gw.py script, driven by request params instead of config.py.
"""
import pandas as pd
import httpx

from app import analysis, cache, charts
from app.fpl_client import FPLError, current_gameweek  # noqa: F401 (re-exported for main.py)
from app import fpl_client

DIFFERENTIAL_OWNERSHIP_THRESHOLD = 0.20
N_MOST_OWNED = 15
N_DIFFERENTIALS = 10

# Display order and titles for both the web report and the PDF.
CHART_FILES = [
    ("top3_current_standings.png", "League Standings"),
    ("top3_rank_history.png", "Top 3: Rank Progression"),
    ("top3_stats.png", "Top 3: Weeks at #1 / Top 3"),
    ("top3_detailed_stats.png", "Top 3: Gameweek Detail"),
    ("active_chips_GW{gw}.png", "Active Chips"),
    ("captaincy_GW{gw}.png", "Captaincy"),
    ("most_owned_GW{gw}.png", "Most Owned Players"),
    ("differentials_by_price_GW{gw}.png", "Differentials by Price"),
    ("differentials_by_points_GW{gw}.png", "Differentials by Points"),
    ("transfers_in_GW{gw}.png", "Transfers In"),
    ("transfers_out_GW{gw}.png", "Transfers Out"),
]


async def _get_bootstrap(client: httpx.AsyncClient) -> dict:
    return await cache.get_or_fetch(
        "bootstrap", cache.LIVE_GW_TTL_SECONDS, lambda: fpl_client.fetch_bootstrap(client)
    )


async def get_current_gw() -> int:
    async with httpx.AsyncClient() as client:
        bootstrap = await _get_bootstrap(client)
    return current_gameweek(bootstrap)


async def build_report(league_id_raw: str, gw_raw: str) -> dict:
    """Returns the dict the templates render, or raises FPLError with a user-facing message."""
    league_id = fpl_client.validate_league_id(league_id_raw)

    async with httpx.AsyncClient() as client:
        bootstrap = await _get_bootstrap(client)
        gw = fpl_client.validate_gameweek(gw_raw, bootstrap)
        event_info = fpl_client.get_event_info(bootstrap, gw)
        ttl = cache.gw_ttl(event_info)

        league_key = cache.make_key(league_id, gw, "league")
        league_data = await cache.get_or_fetch(
            league_key, ttl, lambda: fpl_client.fetch_league(client, league_id)
        )
        fpl_client.check_league_size(league_data)

        league_name = league_data["league"].get("name", f"League {league_id}")
        entry_to_player = fpl_client.entry_to_player_mapping(league_data)
        entry_ids = list(entry_to_player.keys())

        player_to_id, player_to_price, player_to_points = analysis.player_mappings(bootstrap)

        histories_key = cache.make_key(league_id, gw, "histories")
        histories = await cache.get_or_fetch(
            histories_key, ttl, lambda: fpl_client.fetch_histories(client, entry_ids)
        )

        curr_picks_key = cache.make_key(league_id, gw, "picks")
        curr_picks = await cache.get_or_fetch(
            curr_picks_key, ttl, lambda: fpl_client.fetch_picks_for_gw(client, entry_ids, gw)
        )

        prev_picks: dict = {}
        if gw > 1:
            prev_ttl = cache.gw_ttl(fpl_client.get_event_info(bootstrap, gw - 1))
            prev_picks_key = cache.make_key(league_id, gw - 1, "picks")
            prev_picks = await cache.get_or_fetch(
                prev_picks_key, prev_ttl, lambda: fpl_client.fetch_picks_for_gw(client, entry_ids, gw - 1)
            )

    save_dir = cache.report_output_dir(league_id, gw)

    gw_history_df = analysis.build_gw_history_df(entry_to_player, histories)
    top3_analysis = analysis.get_top3_ranking_history(gw_history_df)

    prev_gw_standings = analysis.get_standings_for_gw(gw_history_df, gw - 1) if gw > 1 else pd.DataFrame()
    charts.plot_cover_page(league_name, gw, str(save_dir))
    if not prev_gw_standings.empty:
        charts.plot_top3_current_standings(prev_gw_standings, save_dir=str(save_dir))
    if not top3_analysis["rank_history"].empty:
        charts.plot_top3_rank_history(top3_analysis["rank_history"], top3_analysis["top3_names"], save_dir=str(save_dir))
    charts.plot_top3_stats(top3_analysis["rank_stats"], save_dir=str(save_dir))

    detailed_stats = analysis.build_top3_detailed_stats(
        top3_names=top3_analysis["top3_names"],
        entry_to_player=entry_to_player,
        curr_picks_by_entry=curr_picks,
        prev_picks_by_entry=prev_picks,
        histories_by_entry=histories,
        player_to_id=player_to_id,
    )
    charts.plot_top3_detailed_stats(top3_analysis["top3_names"], detailed_stats, save_dir=str(save_dir))

    team_df = analysis.build_team_summary(curr_picks, player_to_id, player_to_price, player_to_points)

    if not team_df.empty:
        chips = analysis.get_active_chips(curr_picks)
        if chips:
            charts.plot_active_chips(chips, gw, save_dir=str(save_dir))

        charts.plot_captaincy(team_df, gw, save_dir=str(save_dir))
        charts.plot_most_owned(team_df, gw, n=N_MOST_OWNED, save_dir=str(save_dir))

        own_max = max(1, int(len(entry_ids) * DIFFERENTIAL_OWNERSHIP_THRESHOLD))
        charts.plot_differentials_by_price(team_df, gw, own_max, top_n=N_DIFFERENTIALS, save_dir=str(save_dir))
        charts.plot_differentials_by_points(team_df, gw, own_max, top_n=N_DIFFERENTIALS, save_dir=str(save_dir))

        df_in, df_out = analysis.build_transfers(prev_picks, curr_picks, player_to_id)
        if not df_in.empty or not df_out.empty:
            charts.plot_transfers(df_in, df_out, gw, save_dir=str(save_dir))

    charts_present = [
        {"name": name_tpl.format(gw=gw), "title": title}
        for name_tpl, title in CHART_FILES
        if (save_dir / name_tpl.format(gw=gw)).exists()
    ]
    chart_names = [c["name"] for c in charts_present]

    return {
        "league_id": league_id,
        "league_name": league_name,
        "gw": gw,
        "manager_count": len(entry_ids),
        "charts": charts_present,
        "chart_names": chart_names,
        "chart_base_url": f"/reports/league_{league_id}/GW{gw}",
    }

