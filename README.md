# FPL League Reports

A website for generating gameweek reports for any [Fantasy Premier League](https://fantasy.premierleague.com/) classic league — standings, captaincy, most-owned players, differentials, transfers, and a "top 3 managers" deep dive. View it in the browser or download it as a PDF.

Enter any league's ID and a gameweek, and the site fetches fresh data from the official FPL API, generates the charts, and renders the report. Finished gameweeks are cached indefinitely (their data never changes); the current/live gameweek is cached briefly.

## Running locally

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://127.0.0.1:8000.

## Running tests

```bash
pytest
```

Tests cover the pure logic — cache TTL selection, ranking/standings math, and the league-size cap — against fixture data, with no live network calls.

## How a league ID is found

Fantasy → Leagues & Cups → select your league. The ID is the number before `/standings/` in the URL, e.g. for `fantasy.premierleague.com/leagues/1078291/standings/c` the league ID is `1078291`.

## Notes

- Leagues larger than 200 managers aren't supported yet — the per-manager charts (captaincy, most owned, differentials, transfers) require one API call per manager, and very large leagues would be slow and put unnecessary load on the FPL API.
- Reports are generated on demand rather than on a fixed schedule, since any visitor can request any public league.
- The `app/` package is the whole application: `fpl_client.py` (fetching + validation), `cache.py` (the disk cache), `analysis.py` (pure data transforms), `charts.py` (matplotlib rendering), `report.py` (orchestration), `pdf.py` (PDF assembly), and `main.py` (the FastAPI routes).

## Deploying

`render.yaml` deploys this as a free Python web service on [Render](https://render.com) — connect the GitHub repo and it builds/runs from that config automatically. The on-disk cache is ephemeral on the free tier (it repopulates after a redeploy), which is an accepted tradeoff for now.
