#!/usr/bin/env python3
"""
Starting Hand Coverage Checker for Terraforming Mars Games

This script checks how many games have starting_hand data under player_id in the players section.
It leverages the existing tm_data_analyzer.py for basic functionality and filtering.
"""

import sys
import json
from pathlib import Path

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

from tm_data_analyzer import TerraformingMarsAnalyzer

def check_starting_hand_coverage(analyzer: TerraformingMarsAnalyzer) -> dict:
    """
    Check starting hand coverage in the loaded games.
    
    Args:
        analyzer: Initialized TerraformingMarsAnalyzer instance with loaded games
        
    Returns:
        Dictionary with coverage statistics
    """
    if not analyzer.games_data:
        print("No games loaded. Please run load_all_games() first.")
        return {}
    
    games_with_starting_hand = 0
    games_without_starting_hand = 0
    total_players_checked = 0
    games_with_starting_hand_details = []
    
    # Track conceded games
    games_conceded = 0
    games_not_conceded = 0
    games_with_conceded_param = 0
    games_without_conceded_param = 0
    
    for game in analyzer.games_data:
        replay_id = game.get('replay_id', 'unknown')
        players = game.get('players', {})
        game_has_starting_hand = False
        game_starting_hand_info = []
        game_has_preludes = False # Initialize for each game
        
        # Check if game was conceded
        if 'conceded' in game:
            games_with_conceded_param += 1
            game_conceded = game['conceded']
            if game_conceded:
                games_conceded += 1
            else:
                games_not_conceded += 1
        else:
            games_without_conceded_param += 1
            game_conceded = None  # No conceded parameter present
        
        for player_id, player_data in players.items():
            if isinstance(player_data, dict):
                total_players_checked += 1
                if 'starting_hand' in player_data:
                    game_has_starting_hand = True
                    
                    # Check for presence of key starting hand sections
                    starting_hand = player_data['starting_hand']
                    section_info = []
                    
                    if isinstance(starting_hand, dict):
                        # Check corporations (always present, don't show)
                        has_corporations = 'corporations' in starting_hand and starting_hand['corporations']
                        
                        # Check project cards (always present, don't show)
                        has_project_cards = 'project_cards' in starting_hand and starting_hand['project_cards']
                        
                        # Check preludes (optional, only show if present)
                        has_preludes = 'preludes' in starting_hand and starting_hand['preludes']
                        if has_preludes:
                            section_info.append("preludes")
                            game_has_preludes = True
                        
                        # Check for data inconsistencies (missing required sections)
                        if not has_corporations:
                            section_info.append("MISSING corporations")
                        if not has_project_cards:
                            section_info.append("MISSING project_cards")
                        
                        # Only add player info if there are non-default sections to show
                        if section_info:
                            game_starting_hand_info.append(f"Player {player_id}: {', '.join(section_info)}")
                        else:
                            # If only default sections present, just note the player has starting hand
                            game_starting_hand_info.append(f"Player {player_id}: starting hand (default sections only)")
                    else:
                        # Fallback for non-dict format
                        game_starting_hand_info.append(f"Player {player_id}: unknown format")
        
        if game_has_starting_hand:
            games_with_starting_hand += 1
            games_with_starting_hand_details.append({
                'replay_id': replay_id,
                'starting_hand_info': game_starting_hand_info,
                'has_preludes': game_has_preludes,
                'conceded': game_conceded
            })
        else:
            games_without_starting_hand += 1
    
    # Count games with/without preludes among those that have starting hand data
    games_with_preludes = sum(1 for game in games_with_starting_hand_details if game['has_preludes'])
    games_without_preludes = len(games_with_starting_hand_details) - games_with_preludes
    
    # Count conceded games among those with starting hand data
    games_with_starting_hand_conceded = sum(1 for game in games_with_starting_hand_details if game['conceded'])
    games_with_starting_hand_not_conceded = len(games_with_starting_hand_details) - games_with_starting_hand_conceded
    
    coverage_stats = {
        'total_games': len(analyzer.games_data),
        'games_with_starting_hand': games_with_starting_hand,
        'games_without_starting_hand': games_without_starting_hand,
        'total_players_checked': total_players_checked,
        'coverage_percentage': round((games_with_starting_hand / len(analyzer.games_data)) * 100, 2) if analyzer.games_data else 0,
        'games_with_starting_hand_details': games_with_starting_hand_details,
        'conceded_coverage': {
            'games_with_conceded_param': games_with_conceded_param,
            'games_without_conceded_param': games_without_conceded_param,
            'conceded_param_coverage': round((games_with_conceded_param / len(analyzer.games_data)) * 100, 2) if analyzer.games_data else 0,
            'total_games_conceded': games_conceded,
            'total_games_not_conceded': games_not_conceded,
            'conceded_percentage': round((games_conceded / len(analyzer.games_data)) * 100, 2) if analyzer.games_data else 0,
            'games_with_starting_hand_conceded': games_with_starting_hand_conceded,
            'games_with_starting_hand_not_conceded': games_with_starting_hand_not_conceded,
            'conceded_percentage_with_starting_hand': round((games_with_starting_hand_conceded / games_with_starting_hand) * 100, 2) if games_with_starting_hand > 0 else 0
        },
        'prelude_coverage': {
            'games_with_preludes': games_with_preludes,
            'games_without_preludes': games_without_preludes,
            'prelude_percentage': round((games_with_preludes / games_with_starting_hand) * 100, 2) if games_with_starting_hand > 0 else 0,
            'total_games_with_preludes': games_with_preludes,
            'total_games_without_preludes': games_without_preludes
        }
    }
    
    print(f"\nStarting Hand Coverage Analysis:")
    print(f"Total games: {coverage_stats['total_games']}")
    print(f"Games with starting_hand: {coverage_stats['games_with_starting_hand']}")
    print(f"Games without starting_hand: {coverage_stats['games_without_starting_hand']}")
    print(f"Coverage: {coverage_stats['coverage_percentage']}%")
    print(f"Total players checked: {coverage_stats['total_players_checked']}")
    
    # Show conceded coverage
    print(f"\nConceded Parameter Coverage:")
    print(f"Games with 'conceded' parameter: {games_with_conceded_param}")
    print(f"Games without 'conceded' parameter: {games_without_conceded_param}")
    print(f"Conceded parameter coverage: {coverage_stats['conceded_coverage']['conceded_param_coverage']}%")
    print(f"\nConceded Games (among those with parameter):")
    print(f"Games conceded: {games_conceded}")
    print(f"Games not conceded: {games_not_conceded}")
    if games_with_conceded_param > 0:
        conceded_rate = round((games_conceded / games_with_conceded_param) * 100, 2)
        print(f"Conceded rate: {conceded_rate}%")
    if games_with_starting_hand > 0:
        print(f"\nGames with starting hand conceded: {games_with_starting_hand_conceded}")
        print(f"Games with starting hand not conceded: {games_with_starting_hand_not_conceded}")
        print(f"Conceded percentage (among games with starting hand): {coverage_stats['conceded_coverage']['conceded_percentage_with_starting_hand']}%")
    
    # Show prelude coverage among games with starting hand data
    if games_with_starting_hand > 0:
        print(f"\nPrelude Coverage (among games with starting hand data):")
        print(f"Games with preludes: {games_with_preludes}")
        print(f"Games without preludes: {games_without_preludes}")
        print(f"Prelude coverage: {coverage_stats['prelude_coverage']['prelude_percentage']}%")
    
    return coverage_stats

def save_coverage_stats(coverage_stats: dict, output_dir: str = CARD_SUMMARY_ANALYSIS_DIR):
    """
    Save coverage statistics to a JSON file.
    
    Args:
        coverage_stats: Dictionary with coverage statistics
        output_dir: Directory to save output files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save coverage statistics to JSON
    filename = "starting_hand_coverage_stats.json"
    file_path = output_path / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(coverage_stats, f, indent=2, default=str)
    
    # Show file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"\nCoverage statistics saved to: {file_path} (size: {file_size_mb:.1f} MB)")
    
    return file_path

def main():
    """
    Main function to run the starting hand coverage checker.
    """
    # Parse command line arguments
    use_cache = USE_CACHE_BY_DEFAULT
    
    if len(sys.argv) > 1:
        if '--no-cache' in sys.argv:
            use_cache = False
    
    # Initialize analyzer with path from config (reusing existing functionality)
    analyzer = TerraformingMarsAnalyzer(DATA_DIRECTORY)
    
    # Load filtered games (reusing existing functionality)
    print("Starting Hand Coverage Checker for Terraforming Mars")
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
    
    # Check starting hand coverage
    coverage_stats = check_starting_hand_coverage(analyzer)
    
    # Save coverage statistics to file
    if coverage_stats:
        save_coverage_stats(coverage_stats)
    
    print("\nAnalysis complete!")
    print("\nUsage tips:")
    print("- Use --no-cache to force reload all files")
    print("- Example: python check_starting_hand_coverage.py --no-cache")
    print("\nConfiguration:")
    print("- Update config.py to change data directory and other settings")

if __name__ == "__main__":
    main() 