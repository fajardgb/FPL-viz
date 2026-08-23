# ── Key Parameters ────────────────────────────────────────────────────────────
LEAGUE_ID = "555654"   # Change to your league's ID
GAMEWEEK = int(1)      # Change to the gameweek you want to analyze (1-38)

# ── Differential Definition ───────────────────────────────────────────────────
# A player is a "differential" if owned by fewer than this fraction of the league
DIFFERENTIAL_OWNERSHIP_THRESHOLD = 0.20  # % of managers

# ── Plot Settings ─────────────────────────────────────────────────────────────
N_MOST_OWNED = 15       # how many players to show in "most owned" chart
N_DIFFERENTIALS = 10   # how many players to show in each differential chart

# ── Paths ─────────────────────────────────────────────────────────────────────
FPL_PLAYER_DATA_DIR = "fpl_player_data"
