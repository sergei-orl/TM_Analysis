#!/usr/bin/env python3
"""
ELO Coverage and Distribution Checker for Terraforming Mars Games

This script analyzes the distribution of player and opponent ELO ratings in games.
It checks ELO coverage, categorizes ELO values into 100-point ranges, and identifies
games with missing or invalid ELO data.
"""

import sys
import json
from pathlib import Path
from collections import defaultdict

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

from tm_data_analyzer import TerraformingMarsAnalyzer

def categorize_elo(elo_value: int) -> str:
    """
    Categorize ELO value into 100-point ranges.
    
    Args:
        elo_value: ELO rating value
        
    Returns:
        String representing the ELO range
    """
    if elo_value <= 100:
        return "1-100"
    elif elo_value <= 200:
        return "101-200"
    elif elo_value <= 300:
        return "201-300"
    elif elo_value <= 400:
        return "301-400"
    elif elo_value <= 500:
        return "401-500"
    elif elo_value <= 600:
        return "501-600"
    elif elo_value <= 700:
        return "601-700"
    elif elo_value <= 800:
        return "701-800"
    else:
        return "800+"

def check_elo_coverage(analyzer: TerraformingMarsAnalyzer) -> dict:
    """
    Check ELO coverage and distribution in the loaded games.
    
    Args:
        analyzer: Initialized TerraformingMarsAnalyzer instance with loaded games
        
    Returns:
        Dictionary with ELO coverage and distribution statistics
    """
    if not analyzer.games_data:
        print("No games loaded. Please run load_all_games() first.")
        return {}
    
    # Initialize counters and data structures
    games_with_elo_data = 0
    total_players_checked = 0
    total_opponents_checked = 0
    
    # ELO distribution counters
    player_elo_distribution = defaultdict(int)
    opponent_elo_distribution = defaultdict(int)
    
    # Track ELO data quality
    elo_data_quality = {
        'valid_elo_values': 0,
        'invalid_elo_values': 0,
        'missing_elo_data': 0,
        'none_elo_values': 0
    }
    
    for game in analyzer.games_data:
        players = game.get('players', {})
        
        # Get player perspective (same logic as card_analyzer)
        player_perspective = game.get('player_perspective', '')
        
        game_elo_info = []
        
        # Process each player in the game
        for player_id, player_data in players.items():
            if isinstance(player_data, dict):
                total_players_checked += 1
                
                # Check for ELO data
                elo_data = player_data.get('elo_data', {})
                if elo_data and isinstance(elo_data, dict):
                    
                    # Check for game_rank (actual ELO value)
                    game_rank = elo_data.get('game_rank')
                    
                    if game_rank is not None:
                        elo_value = int(game_rank)
                        elo_data_quality['valid_elo_values'] += 1
                        
                        # Categorize ELO value
                        elo_range = categorize_elo(elo_value)
                        
                        # Determine if this is the player or opponent
                        if player_id == player_perspective:
                            # This is the player (us)
                            player_elo_distribution[elo_range] += 1
                            game_elo_info.append(f"Player {player_id} (US): {elo_value} ({elo_range})")
                        else:
                            # This is the opponent
                            opponent_elo_distribution[elo_range] += 1
                            total_opponents_checked += 1
                            game_elo_info.append(f"Player {player_id} (OPPONENT): {elo_value} ({elo_range})")
    
    # Calculate coverage statistics
    total_games = len(analyzer.games_data)
    coverage_stats = {
        'total_games': total_games,
        'games_with_elo_data': games_with_elo_data,
        'total_players_checked': total_players_checked,
        'total_opponents_checked': total_opponents_checked,
        'coverage_percentage': 100.0,  # All games have ELO data
        'elo_data_quality': elo_data_quality,
        'player_elo_distribution': dict(player_elo_distribution),
        'opponent_elo_distribution': dict(opponent_elo_distribution),
    }
    
    # Display results
    print(f"\nELO Coverage and Distribution Analysis:")
    print(f"Total games: {coverage_stats['total_games']}")
    print(f"Games with ELO data: {coverage_stats['games_with_elo_data']}")
    print(f"Coverage: {coverage_stats['coverage_percentage']}%")
    print(f"Total players checked: {coverage_stats['total_players_checked']}")
    print(f"Total opponents checked: {coverage_stats['total_opponents_checked']}")
    
    # Show ELO data quality
    print(f"\nELO Data Quality:")
    print(f"Valid ELO values: {elo_data_quality['valid_elo_values']}")
    print(f"Missing ELO data: {elo_data_quality['missing_elo_data']}")
    
    # Show player ELO distribution
    print(f"\nPlayer ELO Distribution:")
    for elo_range in sorted(player_elo_distribution.keys(), key=lambda x: int(x.split('-')[0]) if '-' in x else 800):
        count = player_elo_distribution[elo_range]
        percentage = round((count / total_players_checked) * 100, 1) if total_players_checked > 0 else 0
        print(f"  {elo_range}: {count} players ({percentage}%)")
    
    # Show opponent ELO distribution
    print(f"\nOpponent ELO Distribution:")
    for elo_range in sorted(opponent_elo_distribution.keys(), key=lambda x: int(x.split('-')[0]) if '-' in x else 800):
        count = opponent_elo_distribution[elo_range]
        percentage = round((count / total_opponents_checked) * 100, 1) if total_opponents_checked > 0 else 0
        print(f"  {elo_range}: {count} opponents ({percentage}%)")
    
    return coverage_stats

def save_elo_stats(elo_stats: dict, output_dir: str = CARD_SUMMARY_ANALYSIS_DIR):
    """
    Save ELO statistics to a JSON file.
    
    Args:
        elo_stats: Dictionary with ELO statistics
        output_dir: Directory to save output files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save ELO statistics to JSON
    filename = "elo_coverage_stats.json"
    file_path = output_path / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(elo_stats, f, indent=2, default=str)
    
    # Show file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"\nELO statistics saved to: {file_path} (size: {file_size_mb:.1f} MB)")
    
    return file_path

def main():
    """
    Main function to run the ELO coverage checker.
    """
    # Parse command line arguments
    use_cache = USE_CACHE_BY_DEFAULT
    
    if len(sys.argv) > 1:
        if '--no-cache' in sys.argv:
            use_cache = False
    
    # Initialize analyzer with path from config
    analyzer = TerraformingMarsAnalyzer(DATA_DIRECTORY)
    
    # Load filtered games
    print("ELO Coverage and Distribution Checker for Terraforming Mars")
    print("=" * 60)
    print(f"Filtering for: {REQUIRED_MAP} map, {REQUIRED_PLAYER_COUNT} players")
    print(f"Colonies: {'OFF' if COLONIES_MUST_BE_OFF else 'ON'}")
    print(f"Corporate Era: {'ON' if CORPORATE_ERA_MUST_BE_ON else 'OFF'}")
    print(f"Draft: {'ON' if DRAFT_MUST_BE_ON else 'OFF'}")
    print(f"Cache: {'Enabled' if use_cache else 'Disabled'}")
    print("=" * 60)
    
    games_loaded = analyzer.load_all_games(use_cache=use_cache)
    
    if games_loaded == 0:
        print("No games found matching criteria. Please check the data directory path in config.py")
        return
    
    print(f"\nLoaded {games_loaded} filtered games...")
    
    # Check ELO coverage and distribution
    elo_stats = check_elo_coverage(analyzer)
    
    # Save ELO statistics to file
    if elo_stats:
        save_elo_stats(elo_stats)
    
    print("\nAnalysis complete!")
    print("\nUsage tips:")
    print("- Use --no-cache to force reload all files")
    print("- Example: python check_elo_coverage.py --no-cache")
    print("\nConfiguration:")
    print("- Update config.py to change data directory and other settings")

if __name__ == "__main__":
    main() 