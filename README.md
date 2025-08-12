# Terraforming Mars Data Analyzer

A Python tool for analyzing Terraforming Mars game data stored in JSON format.

## Setup

1. **Copy the configuration template:**
   ```bash
   cp config_template.py config.py
   ```

2. **Edit `config.py` with your local settings:**
   - Update `DATA_DIRECTORY` to point to your Terraforming Mars game data folder
   - Modify other settings as needed (card names, game criteria, etc.)
   - Optionally configure Google Sheets integration for CSV uploads

3. **Install dependencies:**
   ```bash
   pip install tqdm gspread google-auth
   ```

## Usage

### Basic Analysis
```bash
python tm_data_analyzer.py
```

### Analyze a Specific Card
```bash
python tm_data_analyzer.py --card "Standard Technology"
```

### Analyze a Specific Game Replay
```bash
python tm_data_analyzer.py --replay 123456789
```

### Force Reload (No Cache)
```bash
python tm_data_analyzer.py --no-cache
```

### Run Multi-Card Analysis
```bash
# Analyze all cards from card_list.txt
python run_card_analysis.py

# Analyze with custom cards
python run_card_analysis.py --cards "Cloud Seeding,Lunar Beam,Standard Technology"

# Force reload without cache
python run_card_analysis.py --no-cache
```

### Create Card Summary CSV
```bash
# Create CSV summaries of all analyzed cards
python create_card_summary_csv.py

# Create with custom output prefix
python create_card_summary_csv.py my_summary

# Upload to Google Sheets (if configured)
python create_card_summary_csv.py -u
```

### Analyze Winner-ELO Mismatches
```bash
# Analyze winner vs ELO gainer mismatches
python analyze_winner_elo_mismatch.py

# Force reload without cache
python analyze_winner_elo_mismatch.py --no-cache
```

## Configuration

The `config.py` file contains all configurable settings:

- **Data Directory**: Path to your game data files
- **Default Card**: Card to analyze when no `--card` argument is provided
- **Game Criteria**: Map type, player count, game settings
- **Cache Settings**: Whether to use caching by default
- **CSV Settings**: Default output prefix and analysis directory
- **Google Sheets**: Optional integration for CSV uploads

- `config_template.py` is included as a reference
- Update `config.py` for your local environment

## Output

Analysis results are saved to the `analysis_output/` directory:
- Card analysis JSON files
- Cache files for faster subsequent runs
- Cache hash for detecting data changes

### CSV Summaries

The `create_card_summary_csv.py` script creates two comprehensive CSV files:
- **Values CSV**: Contains all individual statistics and counts
- **Dicts CSV**: Contains detailed dictionary data as JSON strings

These can optionally be uploaded to Google Sheets if configured.

### Multi-Card Analysis

The `run_card_analysis.py` script processes multiple cards sequentially:
- Loads card list from `card_list.txt` by default
- Supports custom card lists via command line
- Processes each card individually with progress tracking
- Useful for batch analysis of multiple cards

### Winner-ELO Analysis

The `analyze_winner_elo_mismatch.py` script analyzes:
- Cases where the game winner doesn't match the ELO gainer
- Special cases like novice ELO gains and zero-gain scenarios
- Results saved to `winner_elo_analysis.txt` 