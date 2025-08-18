"""
Script to create comprehensive CSV summaries of all card analysis data.
Reads all card_analysis_*.json files and creates three CSV files:
1. card_summary_values.csv - Contains all individual values and counts
2. card_summary_dicts.csv - Contains only the dictionary summaries
3. card_summary_interactions.csv - Contains card interaction data (draw methods, seen methods, etc.)

Optionally uploads to Google Sheets with -u or --update_sheets flag.
"""

import json
import csv
from pathlib import Path
from typing import Dict, Any, Set, List
import glob
import argparse
import gspread
from google.oauth2.service_account import Credentials
from google.auth.exceptions import GoogleAuthError

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    import sys
    sys.exit(1)

# Global constants for sheet names
VALUES_SHEET_NAME = 'Values'
DICTS_SHEET_NAME = 'Dicts'
INTERACTIONS_SHEET_NAME = 'Card Interactions'

# Global constants for file names
VALUES_FILE_SUFFIX = '_values.csv'
DICTS_FILE_SUFFIX = '_dicts.csv'
INTERACTIONS_FILE_SUFFIX = '_interactions.csv'

# Global field mapping - single source of truth for all CSV fields
CSV_FIELD_MAPPING = {
    # Basic card info
    'basic_info': [
        ('card_name', 'card_name'),
        ('total_games_analyzed', 'total_games_analyzed'),
        ('total_games_with_card', 'total_games_with_card'),
        ('games_with_prelude', 'prelude_stats.games_with_prelude'),
        ('drawn_count', 'drawn_count'),
        ('played_count', 'played_count'),
    ],
    
    # Win statistics and ELO gains by case (grouped)
    'win_stats': [
        ('win_rate_overall', 'win_rate_by_case.overall'),
        ('elo_gain_overall', 'elo_metrics_by_case.overall.average_elo_gain'),
        ('win_rate_when_seen', 'win_rate_by_case.when_seen'),
        ('elo_gain_when_seen', 'elo_metrics_by_case.when_seen.average_elo_gain'),
        ('win_rate_when_drawn', 'win_rate_by_case.when_drawn'),
        ('elo_gain_when_drawn', 'elo_metrics_by_case.when_drawn.average_elo_gain'),
        ('win_rate_when_bought_during_game', 'win_rate_by_case.when_bought_during_game'),
        ('elo_gain_when_bought_during_game', 'elo_metrics_by_case.when_bought_during_game.average_elo_gain'),
        ('win_rate_when_played', 'win_rate_by_case.when_played'),
        ('elo_gain_when_played', 'elo_metrics_by_case.when_played.average_elo_gain'),
    ],
    
    # Win counts by case
    'win_counts': [
        ('win_count_overall', 'win_count_by_case.overall'),
        ('win_count_when_seen', 'win_count_by_case.when_seen'),
        ('win_count_when_drawn', 'win_count_by_case.when_drawn'),
        ('win_count_when_bought_during_game', 'win_count_by_case.when_bought_during_game'),
        ('win_count_when_played', 'win_count_by_case.when_played'),
    ],
    
    # Average ELO by case
    'avg_elo': [
        ('avg_elo_overall', 'elo_metrics_by_case.overall.average_elo'),
        ('avg_elo_when_seen', 'elo_metrics_by_case.when_seen.average_elo'),
        ('avg_elo_when_drawn', 'elo_metrics_by_case.when_drawn.average_elo'),
        ('avg_elo_when_bought_during_game', 'elo_metrics_by_case.when_bought_during_game.average_elo'),
        ('avg_elo_when_played', 'elo_metrics_by_case.when_played.average_elo'),
    ],
    
    # Starting hand statistics
    'starting_hand': [
        ('play_to_keep_rate', 'starting_hand_stats.play_to_keep_rate'),
        ('keep_rate', 'starting_hand_stats.keep_rate'),
        ('kept_in_starting_hand', 'starting_hand_stats.kept_in_starting_hand'),
        ('kept_and_played', 'starting_hand_stats.kept_and_played'),
        ('kept_but_not_played', 'starting_hand_stats.kept_but_not_played'),
    ],
    
    # Draft and buy statistics
    'draft_buy': [
        ('buy_to_draft_rate', 'draft_buy_stats.buy_to_draft_rate'),
        ('buy_to_draft_1_rate', 'draft_buy_stats.buy_to_draft_1_rate'),
        ('buy_to_draft_2_rate', 'draft_buy_stats.buy_to_draft_2_rate'),
        ('buy_to_draft_3_rate', 'draft_buy_stats.buy_to_draft_3_rate'),
        ('buy_to_draft_4_rate', 'draft_buy_stats.buy_to_draft_4_rate'),
        ('draft_1_buys', 'draft_buy_stats.draft_1_buys'),
        ('draft_2_buys', 'draft_buy_stats.draft_2_buys'),
        ('draft_3_buys', 'draft_buy_stats.draft_3_buys'),
        ('draft_4_buys', 'draft_buy_stats.draft_4_buys'),
    ],
    
    # Play rate statistics
    'play_rates': [
        ('play_to_buy_during_game_rate', 'play_rate_stats.play_to_buy_during_game_rate'),
        ('play_to_buy_overall_rate', 'play_rate_stats.play_to_buy_overall_rate'),
        ('play_to_draw_for_free_rate', 'play_rate_stats.play_to_draw_for_free_rate'),
        ('play_per_option_rate', 'play_rate_stats.play_per_option_rate'),
        ('play_per_card_in_hand_rate', 'play_rate_stats.play_per_card_in_hand_rate'),
        ('plays_when_bought_during_game', 'play_rate_stats.plays_when_bought_during_game'),
        ('plays_when_bought_overall', 'play_rate_stats.plays_when_bought_overall'),
        ('plays_when_drawn_for_free', 'play_rate_stats.plays_when_drawn_for_free'),
        ('plays_when_card_was_keepable', 'play_rate_stats.plays_when_card_was_keepable'),
        ('plays_when_card_was_in_hand', 'play_rate_stats.plays_when_card_was_in_hand'),
    ],
    
    # Keep rates and other rates
    'keep_rates': [
        ('business_contacts_keep_rate', 'keep_rates.business_contacts_keep_rate'),
        ('business_network_buy_rate', 'keep_rates.business_network_buy_rate'),
        ('invention_contest_keep_rate', 'keep_rates.invention_contest_keep_rate'),
        ('inventors_guild_buy_rate', 'keep_rates.inventors_guild_buy_rate'),
        ('draft_1_rate', 'keep_rates.draft_1_rate'),
        ('draft_3_rate', 'keep_rates.draft_3_rate'),
        ('card_buy_through_card_rate', 'keep_rates.card_buy_through_card_rate'),
    ]
}

def get_nested_value(data: Dict[str, Any], path: str, default=None):
    """
    Get a nested value from a dictionary using dot notation.
    
    Args:
        data: Dictionary to search in
        path: Dot-separated path (e.g., 'prelude_stats.games_with_prelude')
        default: Default value if path not found
        
    Returns:
        Value at the path or default
    """
    keys = path.split('.')
    current = data
    
    for key in keys:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return default
    
    return current

def create_values_csv_headers() -> List[str]:
    """
    Create the complete list of CSV headers for the values CSV.
    
    Returns:
        List of CSV column headers
    """
    headers = []
    
    # Flatten all field mappings into a single list
    for section_name, field_mappings in CSV_FIELD_MAPPING.items():
        for csv_header, _ in field_mappings:
            headers.append(csv_header)
    
    return headers

def load_all_card_analyses(analysis_dir: str = None) -> List[Dict[str, Any]]:
    """
    Load all card analysis JSON files from the analysis directory.
    
    Args:
        analysis_dir: Directory containing card analysis files (uses config default if None)
        
    Returns:
        List of card analysis dictionaries
    """
    if analysis_dir is None:
        analysis_dir = CARD_SUMMARY_ANALYSIS_DIR
    
    analysis_path = Path(analysis_dir)
    if not analysis_path.exists():
        print(f"Error: Analysis directory '{analysis_dir}' not found.")
        return []
    
    # Find all card analysis files
    card_files = glob.glob(str(analysis_path / "card_analysis_*.json"))
    
    if not card_files:
        print(f"No card analysis files found in '{analysis_dir}'")
        return []
    
    print(f"Found {len(card_files)} card analysis files")
    
    card_analyses = []
    for file_path in card_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                card_data = json.load(f)
                card_analyses.append(card_data)
                print(f"Loaded: {card_data.get('card_name', 'Unknown')}")
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
    
    print(f"Successfully loaded {len(card_analyses)} card analyses")
    return card_analyses

def collect_all_unique_fields(card_analyses: List[Dict[str, Any]]) -> Dict[str, Set[str]]:
    """
    Collect all unique values for dictionary fields across all cards.
    
    Args:
        card_analyses: List of card analysis dictionaries
        
    Returns:
        Dictionary mapping field names to sets of unique values
    """
    unique_fields = {
        'draw_methods': set(),
        'seen_methods': set(),
        'other_stats': set(),
        'keep_rates': set()
    }
    
    for card in card_analyses:
        # Collect draw_methods
        if 'draw_methods' in card:
            unique_fields['draw_methods'].update(card['draw_methods'].keys())
        
        # Collect seen_methods
        if 'seen_methods' in card:
            unique_fields['seen_methods'].update(card['seen_methods'].keys())
        
        # Collect other_stats
        if 'other_stats' in card:
            unique_fields['other_stats'].update(card['other_stats'].keys())
        
        # Collect keep_rates
        if 'keep_rates' in card:
            unique_fields['keep_rates'].update(card['keep_rates'].keys())
    
    return unique_fields

def create_interactions_csv_headers(unique_fields: Dict[str, Set[str]]) -> List[str]:
    """
    Create the complete list of CSV headers for the interactions CSV.
    
    Args:
        unique_fields: Dictionary of unique field values
        
    Returns:
        List of CSV column headers
    """
    headers = [
        'card_name',
        'total_games_analyzed',
        'total_games_with_card',
    ]
    
    # Add individual draw method columns
    for draw_method in sorted(unique_fields['draw_methods']):
        headers.append(draw_method)
    
    # Add individual seen method columns
    for seen_method in sorted(unique_fields['seen_methods']):
        headers.append(seen_method)
    
    # Add individual other stats columns (without double prefix)
    for other_stat in sorted(unique_fields['other_stats']):
        headers.append(other_stat)
    
    return headers

def _sort_elo_key(elo_key: str) -> int:
    """
    Sort ELO keys in the correct order.
    
    Args:
        elo_key: ELO key string
        
    Returns:
        Integer for sorting
    """
    if elo_key == '-19 and down':
        return -19
    elif elo_key == '19 and up':
        return 19
    elif 'to' in elo_key:
        # Extract the first number from ranges like "-17 to -18"
        parts = elo_key.split(' to ')
        return int(parts[0])
    else:
        # Single values like "0"
        return int(elo_key)

def _sort_gen_pair_key(gen_pair: str) -> tuple:
    """
    Sort generation pair keys in the correct order.
    
    Args:
        gen_pair: Generation pair string like "(1,2)"
        
    Returns:
        Tuple for sorting
    """
    # Remove parentheses and split by comma
    gen_pair = gen_pair.strip('()')
    parts = gen_pair.split(',')
    
    # Handle None values
    drawn = 0 if parts[0] == "None" else int(parts[0])
    played = 0 if parts[1] == "None" else int(parts[1])
    
    # Put zeros at the end, otherwise sort by drawn then played
    if drawn == 0:
        return (999, played)  # Large number to put zeros at the end
    return (drawn, played)

def _sort_payment_tuple_key(payment_key: str) -> tuple:
    """
    Sort payment tuple keys by sum of numbers, then by first number.
    
    Examples of sorting order:
    (1,) -> (1, 1)     # sum=1, first=1
    (1,2) -> (3, 1)    # sum=3, first=1  
    (3,) -> (3, 3)     # sum=3, first=3
    (3,4) -> (7, 3)    # sum=7, first=3
    (6,1) -> (7, 6)    # sum=7, first=6
    (11) -> (11, 11)   # sum=11, first=11
    (12,1) -> (13, 12) # sum=13, first=12
    
    Args:
        payment_key: Payment key string like "(1,2)" or "(3,)"
        
    Returns:
        Tuple for sorting (sum, first_number)
    """
    # Remove parentheses and split by comma
    payment_key = payment_key.strip('()')
    if not payment_key:  # Empty tuple
        return (0, 0)
    
    parts = payment_key.split(',')
    # Convert to integers, handle empty parts
    numbers = []
    for part in parts:
        part = part.strip()
        if part:  # Only add non-empty parts
            try:
                numbers.append(int(part))
            except ValueError:
                numbers.append(0)
    
    if not numbers:  # No valid numbers
        return (0, 0)
    
    # Return (sum, first_number) for sorting
    return (sum(numbers), numbers[0])

def _sort_dict_by_keys(data_dict: dict, key_type: str = 'numeric') -> dict:
    """
    Sort a dictionary by its keys based on the specified key type.
    
    Args:
        data_dict: Dictionary to sort
        key_type: Type of keys ('numeric', 'elo', 'gen_pair', 'string')
        
    Returns:
        Sorted dictionary
    """
    if not data_dict:
        return data_dict
    
    if key_type == 'numeric':
        # Sort numeric keys from lowest to highest (convert to int for proper numeric sorting)
        return dict(sorted(data_dict.items(), key=lambda x: int(x[0])))
    elif key_type == 'elo':
        # Sort ELO keys in the correct order
        return dict(sorted(data_dict.items(), key=lambda x: _sort_elo_key(x[0])))
    elif key_type == 'gen_pair':
        # Sort generation pair keys
        return dict(sorted(data_dict.items(), key=lambda x: _sort_gen_pair_key(x[0])))
    elif key_type == 'payment_tuple':
        # Sort payment tuple keys by sum, then by first number
        return dict(sorted(data_dict.items(), key=lambda x: _sort_payment_tuple_key(x[0])))
    else:
        # Default string sorting
        return dict(sorted(data_dict.items()))

def create_dicts_csv_headers() -> List[str]:
    """
    Create the complete list of CSV headers for the dictionaries CSV.
    
    Returns:
        List of CSV column headers
    """
    headers = [
        'card_name',
        'elo_gains_dict',
        'drawn_by_generation_dict',
        'played_by_generation_dict',
        'draw_free_dict',
        'draw_and_buy_dict',
        'draw_for_2_dict',
        'drawn_and_played_by_gen_dict',
        'drawn_not_played_by_gen_dict',
        'player_corporations_dict',
        'payment_distribution_dict'
    ]
    
    return headers

def extract_values_row(card: Dict[str, Any]) -> List[Any]:
    """
    Extract a single row of data from a card analysis for the values CSV.
    Uses the centralized CSV_FIELD_MAPPING for maintainability.
    
    Args:
        card: Card analysis dictionary
        
    Returns:
        List of values for the CSV row
    """
    row = []
    
    # Process each section of the field mapping
    for section_name, field_mappings in CSV_FIELD_MAPPING.items():
        for csv_header, data_path in field_mappings:
            # Use the helper function to get nested values
            value = get_nested_value(card, data_path, 0)
            row.append(value)
    
    return row

def extract_interactions_row(card: Dict[str, Any], unique_fields: Dict[str, Set[str]]) -> List[Any]:
    """
    Extract a single row of interaction data from a card analysis for the interactions CSV.
    
    Args:
        card: Card analysis dictionary
        unique_fields: Dictionary of unique field values
        
    Returns:
        List of values for the CSV row
    """
    row = []
    
    # Basic card info
    row.append(card.get('card_name', ''))
    row.append(card.get('total_games_analyzed', 0))
    row.append(card.get('total_games_with_card', 0))
    
    # Individual draw method counts
    draw_methods = card.get('draw_methods', {})
    for draw_method in sorted(unique_fields['draw_methods']):
        row.append(draw_methods.get(draw_method, 0))
    
    # Individual seen method counts
    seen_methods = card.get('seen_methods', {})
    for seen_method in sorted(unique_fields['seen_methods']):
        row.append(seen_methods.get(seen_method, 0))
    
    # Individual other stats counts (without double prefix)
    other_stats = card.get('other_stats', {})
    for other_stat in sorted(unique_fields['other_stats']):
        row.append(other_stats.get(other_stat, 0))
    
    return row

def extract_dicts_row(card: Dict[str, Any]) -> List[Any]:
    """
    Extract a single row of dictionary data from a card analysis for the dicts CSV.
    
    Args:
        card: Card analysis dictionary
        
    Returns:
        List of values for the CSV row
    """
    row = []
    
    # Card name
    row.append(card.get('card_name', ''))
    
    # Dictionary summaries (as JSON strings) - properly sorted
    row.append(json.dumps(_sort_dict_by_keys(card.get('elo_gains', {}), 'elo')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('drawn_by_generation', {}), 'numeric')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('played_by_generation', {}), 'numeric')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('draw_free', {}), 'numeric')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('draw_and_buy', {}), 'numeric')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('draw_for_2', {}), 'numeric')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('drawn_and_played_by_gen', {}), 'gen_pair')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('drawn_not_played_by_gen', {}), 'numeric')))
    row.append(json.dumps(_sort_dict_by_keys(card.get('player_corporations', {}), 'string')))
    
    # Payment distribution dictionary - sorted by payment combination
    payment_dist = card.get('payment_distribution', {})
    # Convert tuple keys to strings for JSON serialization
    payment_dist_str = {str(k): v for k, v in payment_dist.items()}
    row.append(json.dumps(_sort_dict_by_keys(payment_dist_str, 'payment_tuple')))
    
    return row

def create_card_summary_csvs(output_prefix: str = None, analysis_dir: str = None):
    """
    Create three comprehensive CSV summary files of all card analysis data.
    
    Args:
        output_prefix: Prefix for output CSV file names (uses config default if None)
        analysis_dir: Directory containing card analysis files (uses config default if None)
    """
    print("Creating card summary CSV files...")
    
    # Load all card analyses
    card_analyses = load_all_card_analyses(analysis_dir)
    if not card_analyses:
        print("No card analyses to process.")
        return
    
    # Collect all unique field values
    print("Collecting unique field values...")
    unique_fields = collect_all_unique_fields(card_analyses)
    
    # Create CSV headers
    values_headers = create_values_csv_headers()
    dicts_headers = create_dicts_csv_headers()
    interactions_headers = create_interactions_csv_headers(unique_fields)
    
    print(f"Created {len(values_headers)} columns for values CSV")
    print(f"Created {len(dicts_headers)} columns for dicts CSV")
    print(f"Created {len(interactions_headers)} columns for interactions CSV")
    
    # Write values CSV file
    values_file = f"{output_prefix}{VALUES_FILE_SUFFIX}"
    print(f"Writing values CSV to {values_file}...")
    with open(values_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(values_headers)
        
        # Write data rows
        for i, card in enumerate(card_analyses):
            row = extract_values_row(card)
            writer.writerow(row)
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(card_analyses)} cards for values CSV...")
    
    # Write dicts CSV file
    dicts_file = f"{output_prefix}{DICTS_FILE_SUFFIX}"
    print(f"Writing dicts CSV to {dicts_file}...")
    with open(dicts_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(dicts_headers)
        
        # Write data rows
        for i, card in enumerate(card_analyses):
            row = extract_dicts_row(card)
            writer.writerow(row)
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(card_analyses)} cards for dicts CSV...")
    
    # Write interactions CSV file
    interactions_file = f"{output_prefix}{INTERACTIONS_FILE_SUFFIX}"
    print(f"Writing interactions CSV to {interactions_file}...")
    with open(interactions_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        
        # Write header
        writer.writerow(interactions_headers)
        
        # Write data rows
        for i, card in enumerate(card_analyses):
            row = extract_interactions_row(card, unique_fields)
            writer.writerow(row)
            
            if (i + 1) % 100 == 0:
                print(f"Processed {i + 1}/{len(card_analyses)} cards for interactions CSV...")
    
    print(f"✅ Successfully created all three CSV files:")
    print(f"  📊 Values CSV: {values_file} ({len(values_headers)} columns)")
    print(f"  📊 Dicts CSV: {dicts_file} ({len(dicts_headers)} columns)")
    print(f"  📊 Interactions CSV: {interactions_file} ({len(interactions_headers)} columns)")
    print(f"📊 Processed {len(card_analyses)} cards total")
    
    # Print summary of unique fields found
    print("\nUnique field counts:")
    for field_name, field_values in unique_fields.items():
        print(f"  {field_name}: {len(field_values)} unique values")

def upload_to_google_sheets(values_file: str, dicts_file: str, interactions_file: str, sheet_id: str = None, credentials_file: str = None):
    """
    Upload CSV data to Google Sheets.
    
    Args:
        values_file: Path to the values CSV file
        dicts_file: Path to the dicts CSV file
        interactions_file: Path to the interactions CSV file
        sheet_id: Google Sheets ID (uses config default if None)
        credentials_file: Path to the service account credentials JSON file (uses config default if None)
    """
    # Use config defaults if not provided
    if sheet_id is None:
        sheet_id = GOOGLE_SHEETS_ID
    if credentials_file is None:
        credentials_file = GOOGLE_CREDENTIALS_FILE
    
    # Check if Google Sheets integration is configured
    if not sheet_id or not credentials_file:
        print("❌ Google Sheets integration not configured.")
        print("   Please set GOOGLE_SHEETS_ID and GOOGLE_CREDENTIALS_FILE in config.py")
        return
    
    try:
        print(f"🔐 Authenticating with Google Sheets...")
        
        # Set up credentials
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = Credentials.from_service_account_file(credentials_file, scopes=scope)
        client = gspread.authorize(creds)
        
        print(f"📊 Opening Google Sheet: {sheet_id}")
        sheet = client.open_by_key(sheet_id)
        
        # Upload values CSV
        print(f"📤 Uploading values CSV to '{VALUES_SHEET_NAME}' worksheet...")
        values_worksheet = sheet.worksheet(VALUES_SHEET_NAME) if VALUES_SHEET_NAME in [ws.title for ws in sheet.worksheets()] else sheet.add_worksheet(title=VALUES_SHEET_NAME, rows=1000, cols=100)
        
        with open(values_file, 'r', encoding='utf-8') as f:
            csv_data = list(csv.reader(f))
        
        # Clear existing data and upload new data
        values_worksheet.clear()
        values_worksheet.update('A1', csv_data)
        print(f"✅ Values CSV uploaded successfully ({len(csv_data)} rows)")
        
        # Upload dicts CSV
        print(f"📤 Uploading dicts CSV to '{DICTS_SHEET_NAME}' worksheet...")
        dicts_worksheet = sheet.worksheet(DICTS_SHEET_NAME) if DICTS_SHEET_NAME in [ws.title for ws in sheet.worksheets()] else sheet.add_worksheet(title=DICTS_SHEET_NAME, rows=1000, cols=50)
        
        with open(dicts_file, 'r', encoding='utf-8') as f:
            csv_data = list(csv.reader(f))
        
        # Clear existing data and upload new data
        dicts_worksheet.clear()
        dicts_worksheet.update('A1', csv_data)
        print(f"✅ Dicts CSV uploaded successfully ({len(csv_data)} rows)")
        
        # Upload interactions CSV
        print(f"📤 Uploading interactions CSV to '{INTERACTIONS_SHEET_NAME}' worksheet...")
        interactions_worksheet = sheet.worksheet(INTERACTIONS_SHEET_NAME) if INTERACTIONS_SHEET_NAME in [ws.title for ws in sheet.worksheets()] else sheet.add_worksheet(title=INTERACTIONS_SHEET_NAME, rows=1000, cols=100)
        
        with open(interactions_file, 'r', encoding='utf-8') as f:
            csv_data = list(csv.reader(f))
        
        # Clear existing data and upload new data
        interactions_worksheet.clear()
        interactions_worksheet.update('A1', csv_data)
        print(f"✅ Interactions CSV uploaded successfully ({len(csv_data)} rows)")
        
        print(f"🎉 All data uploaded to Google Sheets successfully!")
        print(f"🔗 Sheet URL: https://docs.google.com/spreadsheets/d/{sheet_id}")
        
    except FileNotFoundError:
        print(f"❌ Error: Credentials file '{credentials_file}' not found.")
        print(f"   Please ensure the service account JSON file path in config.py is correct.")
    except GoogleAuthError as e:
        print(f"❌ Google authentication error: {e}")
        print(f"   Please check your service account credentials and permissions.")
    except Exception as e:
        print(f"❌ Error uploading to Google Sheets: {e}")
        print(f"   Please check your internet connection and sheet permissions.")

def main():
    """
    Main function to run the card summary CSV creation.
    """
    parser = argparse.ArgumentParser(description='Create comprehensive CSV summaries of card analysis data')
    parser.add_argument('output_prefix', nargs='?', default=None, 
                       help='Prefix for output CSV file names (uses config default if not specified)')
    parser.add_argument('analysis_dir', nargs='?', default=None,
                       help='Directory containing card analysis files (uses config default if not specified)')
    parser.add_argument('-u', '--update_sheets', action='store_true',
                       help='Upload CSV data to Google Sheets (requires Google Sheets configuration in config.py)')
    parser.add_argument('--sheet_id', default=None,
                       help='Google Sheets ID (overrides config setting)')
    parser.add_argument('--credentials', default=None,
                       help='Path to service account credentials JSON file (overrides config setting)')
    
    args = parser.parse_args()
    
    # Use config defaults if not specified
    output_prefix = args.output_prefix if args.output_prefix else CARD_SUMMARY_OUTPUT_PREFIX
    analysis_dir = args.analysis_dir if args.analysis_dir else CARD_SUMMARY_ANALYSIS_DIR
    update_sheets = args.update_sheets
    sheet_id = args.sheet_id
    credentials_file = args.credentials
    
    print("Card Summary CSV Creator")
    print("=" * 40)
    print(f"Output prefix: {output_prefix}")
    print(f"Analysis directory: {analysis_dir}")
    if update_sheets:
        if GOOGLE_SHEETS_ID and GOOGLE_CREDENTIALS_FILE:
            print(f"Google Sheets integration: ENABLED")
            print(f"Sheet ID: {sheet_id or GOOGLE_SHEETS_ID}")
            print(f"Credentials file: {credentials_file or GOOGLE_CREDENTIALS_FILE}")
        else:
            print(f"Google Sheets integration: NOT CONFIGURED")
            print(f"   Please set GOOGLE_SHEETS_ID and GOOGLE_CREDENTIALS_FILE in config.py")
            update_sheets = False
    else:
        print(f"Google Sheets integration: DISABLED")
    print("=" * 40)
    
    # Create CSV files
    create_card_summary_csvs(output_prefix, analysis_dir)
    
    # Upload to Google Sheets if requested and configured
    if update_sheets:
        values_file = f"{output_prefix}{VALUES_FILE_SUFFIX}"
        dicts_file = f"{output_prefix}{DICTS_FILE_SUFFIX}"
        interactions_file = f"{output_prefix}{INTERACTIONS_FILE_SUFFIX}"
        
        # Check if CSV files exist
        if not Path(values_file).exists() or not Path(dicts_file).exists() or not Path(interactions_file).exists():
            print(f"❌ Error: CSV files not found. Cannot upload to Google Sheets.")
            return
        
        print(f"\n🔄 Starting Google Sheets upload...")
        upload_to_google_sheets(values_file, dicts_file, interactions_file, sheet_id, credentials_file)
    
    print("\nUsage:")
    print("  python create_card_summary_csv.py [output_prefix] [analysis_dir]")
    print("  python create_card_summary_csv.py [output_prefix] [analysis_dir] -u")
    print("  Example: python create_card_summary_csv.py my_summary analysis_output -u")
    print("  This will create: my_summary_values.csv, my_summary_dicts.csv, and my_summary_interactions.csv")
    if GOOGLE_SHEETS_ID and GOOGLE_CREDENTIALS_FILE:
        print("  And upload them to Google Sheets (if -u flag is used)")
    else:
        print("  Google Sheets integration requires configuration in config.py")
    print("\nConfiguration:")
    print("  Update config.py to change default settings and enable Google Sheets integration")


if __name__ == "__main__":
    main() 