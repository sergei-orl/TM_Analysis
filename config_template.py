# Configuration template for Terraforming Mars Data Analyzer
# Copy this file to config.py and update the paths for your local environment

# Data directory path - update this to your actual data directory
DATA_DIRECTORY = r"path/to/your/tm/games/data"

# Default card to analyze
DEFAULT_CARD = "Acquired Company"

# Analysis settings
USE_CACHE_BY_DEFAULT = True

# Game filtering criteria
REQUIRED_MAP = "Tharsis"
REQUIRED_PLAYER_COUNT = 2
COLONIES_MUST_BE_OFF = True
CORPORATE_ERA_MUST_BE_ON = True
DRAFT_MUST_BE_ON = True

# Additional filtering options
PRELUDE_MUST_BE_ON = True
MUST_INCLUDE_STARTING_HAND = True
PLAYERS_ELO_OVER_THRESHOLD = False
ELO_THRESHOLD = 300

# Card Summary CSV settings
CARD_SUMMARY_OUTPUT_PREFIX = "card_summary"
CARD_SUMMARY_ANALYSIS_DIR = "analysis_output"

# Google Sheets settings (optional - leave empty to disable)
GOOGLE_SHEETS_ID = ""  # Your Google Sheets ID here
GOOGLE_CREDENTIALS_FILE = ""  # Path to your service account credentials JSON file 