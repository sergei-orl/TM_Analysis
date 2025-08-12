#!/usr/bin/env python3
"""
Script to analyze winner vs player_name mismatches when game_rank_change > 0,
and analyze cases with game_rank_change = 0.
"""

import sys

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

# Import the main analyzer to reuse its functionality
from tm_data_analyzer import TerraformingMarsAnalyzer

def analyze_winner_elo_mismatches(games_data):
    """
    Analyze winner vs ELO gainer mismatches in Terraforming Mars games.
    
    Args:
        games_data: List of game data dictionaries
        
    Returns:
        Tuple of (total_games, winner_elo_cases, mismatch_cases)
    """
    if not games_data:
        print("No games loaded. Please load games first.")
        return 0, [], []
    
    total_games = len(games_data)
    winner_elo_cases = []
    mismatch_cases = []
    winner_reverted_cases = []  # List to collect winner reverted games separately
    zero_gain_matches = 0  # Count of winner with 0 gain, opponent with negative gain
    zero_gain_loss_games = 0 # Count of games where both players have 0 ELO gain and winner has more VP
    winner_reverted_games = 0 # Count of winner reverted games (ELO gainer ≠ winner, but ELO loser = winner)
    novice_elo_gain_1 = 0  # Count of players with game_rank: 1 and game_rank_change: 1
    
    for game in games_data:
        replay_id = game.get('replay_id', 'unknown')
        winner = game.get('winner', 'unknown')
        players = game.get('players', {})
        
        # Extract elo_gainer from players
        elo_gainer = 'unknown'
        elo_gain = 0
        winner_found_in_players = False
        winner_elo_gain = 0
        opponent_elo_gain = 0
        elo_loser = 'unknown'
        elo_loss = 0
        
        for player_id, player_data in players.items():
            if not isinstance(player_data, dict):
                continue
                
            player_name = player_data.get('player_name', 'unknown')
            elo_data = player_data.get('elo_data')
            
            # Check if this player is the winner
            if player_name == winner:
                winner_found_in_players = True
                if elo_data and isinstance(elo_data, dict):
                    game_rank_change = elo_data.get('game_rank_change', 0)
                    if game_rank_change is None:
                        game_rank_change = 0
                    elif not isinstance(game_rank_change, (int, float)):
                        print(f"Invalid game_rank_change for replay_id: {replay_id}, player_id: {player_id}")
                        game_rank_change = 0
                    winner_elo_gain = game_rank_change
                else:
                    # Missing elo_data counts as 0 gain
                    winner_elo_gain = 0
            else:
                # This is the opponent
                if elo_data and isinstance(elo_data, dict):
                    game_rank_change = elo_data.get('game_rank_change', 0)
                    if game_rank_change is None:
                        game_rank_change = 0
                    elif not isinstance(game_rank_change, (int, float)):
                        print(f"Invalid game_rank_change for replay_id: {replay_id}, player_id: {player_id}")
                        game_rank_change = 0
                    opponent_elo_gain = game_rank_change
                else:
                    # Missing elo_data counts as 0 gain
                    opponent_elo_gain = 0
            
            # Find the player with positive game_rank_change (elo_gainer)
            if elo_data and isinstance(elo_data, dict):
                game_rank_change = elo_data.get('game_rank_change', 0)
                
                # Ensure game_rank_change is a valid number
                if game_rank_change is None:
                    game_rank_change = 0
                elif not isinstance(game_rank_change, (int, float)):
                    print(f"Invalid game_rank_change for replay_id: {replay_id}, player_id: {player_id}")
                    game_rank_change = 0
                
                if game_rank_change > 0:
                    elo_gainer = player_name
                    elo_gain = game_rank_change
                    # Check for special case: game_rank: 1 and game_rank_change: 1 (Novice elo gain)
                    if game_rank_change == 1:
                        game_rank = elo_data.get('game_rank', 0)
                        if game_rank == 1:
                            # This is a novice ELO gain case
                            novice_elo_gain_1 += 1
                elif game_rank_change < 0:
                    elo_loser = player_name
                    elo_loss = game_rank_change
        
        # Check for special case: winner found but with 0 gain while opponent has negative gain
        if winner_found_in_players and winner_elo_gain == 0 and opponent_elo_gain < 0:
            # This is a correct case - winner is right, just has 0 ELO gain
            case = {
                'replay_id': replay_id,
                'winner': winner,
                'elo_gainer': winner,  # Winner is the elo_gainer (with 0 gain)
                'elo_gain': 0,
                'is_mismatch': False,  # Not a mismatch
                'is_zero_gain_match': True,  # Special case: winner with 0 gain
                'is_zero_gain_loss_game': False,
                'is_winner_reverted_game': False
            }
            zero_gain_matches += 1
        # Check for 0 gain and loss game: both players have 0 ELO gain, but winner has more final VP
        elif winner_found_in_players and winner_elo_gain == 0 and opponent_elo_gain == 0:
            # Check if winner has more final VP than opponent
            winner_final_vp = 0
            opponent_final_vp = 0
            
            for player_id, player_data in players.items():
                if not isinstance(player_data, dict):
                    continue
                    
                player_name = player_data.get('player_name', 'unknown')
                final_vp = player_data.get('final_vp', 0)
                
                if player_name == winner:
                    winner_final_vp = final_vp
                else:
                    opponent_final_vp = final_vp
            
            if winner_final_vp > opponent_final_vp:
                # This is a 0 gain and loss game - winner has more VP
                case = {
                    'replay_id': replay_id,
                    'winner': winner,
                    'elo_gainer': winner,  # Winner is the elo_gainer (with 0 gain)
                    'elo_gain': 0,
                    'is_mismatch': False,  # Not a mismatch
                    'is_zero_gain_match': False,
                    'is_zero_gain_loss_game': True,  # Special case: 0 gain and loss game
                    'is_winner_reverted_game': False,
                    'winner_vp': winner_final_vp,
                    'opponent_vp': opponent_final_vp
                }
                zero_gain_loss_games += 1
            else:
                # Both have 0 gain but winner doesn't have more VP - this might be a mismatch
                case = {
                    'replay_id': replay_id,
                    'winner': winner,
                    'elo_gainer': elo_gainer,
                    'elo_gain': elo_gain,
                    'is_mismatch': (winner != elo_gainer),
                    'is_zero_gain_match': False,
                    'is_zero_gain_loss_game': False,
                    'is_winner_reverted_game': False
                }
        # Check for winner reverted game: ELO gainer ≠ winner, but ELO loser = winner
        elif winner_found_in_players and elo_gainer != 'unknown' and elo_loser != 'unknown' and elo_gainer != winner and elo_loser == winner:
            # This is a winner reverted game - proper mismatch
            case = {
                'replay_id': replay_id,
                'winner': winner,
                'elo_gainer': elo_gainer,
                'elo_gain': elo_gain,
                'elo_loser': elo_loser,
                'elo_loss': elo_loss,
                'is_mismatch': False,
                'is_zero_gain_match': False,
                'is_zero_gain_loss_game': False,
                'is_winner_reverted_game': True  # Special case: winner reverted game
            }
            winner_reverted_games += 1
            winner_reverted_cases.append(case) # Add to the separate list
        # Check for novice ELO gain case: game_rank: 1 and game_rank_change: 1
        elif winner_found_in_players and elo_gainer != winner and elo_gain == 1:
            # Check if this is a novice ELO gain case
            for player_id, player_data in players.items():
                if not isinstance(player_data, dict):
                    continue
                    
                player_name = player_data.get('player_name', 'unknown')
                if player_name == elo_gainer:
                    elo_data = player_data.get('elo_data')
                    if elo_data and isinstance(elo_data, dict):
                        game_rank = elo_data.get('game_rank', 0)
                        if game_rank == 1:
                            # This is a novice ELO gain case - don't create a case object, just count it
                            # The counter was already incremented earlier, so we skip case creation
                            continue
            case = {
                'replay_id': replay_id,
                'winner': winner,
                'elo_gainer': elo_gainer,
                'elo_gain': elo_gain,
                'is_mismatch': False,
                'is_zero_gain_match': False,
                'is_zero_gain_loss_game': False,
                'is_winner_reverted_game': False
            }
        else:
            # Normal case - check if winner != elo_gainer
            case = {
                'replay_id': replay_id,
                'winner': winner,
                'elo_gainer': elo_gainer,
                'elo_gain': elo_gain,
                'is_mismatch': (winner != elo_gainer),
                'is_zero_gain_match': False,
                'is_zero_gain_loss_game': False,
                'is_winner_reverted_game': False
            }
        
        winner_elo_cases.append(case)
        
        # If there's a mismatch, add to mismatch cases
        if case['is_mismatch']:
            mismatch_cases.append(case)
    
    return total_games, winner_elo_cases, mismatch_cases, winner_reverted_cases, zero_gain_matches, zero_gain_loss_games, winner_reverted_games, novice_elo_gain_1

def save_results_to_file(total_games, winner_elo_cases, mismatch_cases, winner_reverted_cases, zero_gain_matches, zero_gain_loss_games, winner_reverted_games, novice_elo_gain_1, output_file="winner_elo_analysis.txt"):
    """
    Save analysis results to a text file.
    
    Args:
        total_games: Total number of games
        winner_elo_cases: All cases with winner and elo_gainer
        mismatch_cases: Cases where winner != elo_gainer
        output_file: Output file path
    """
    try:
        # Ensure output_file is a string and create proper path
        if not isinstance(output_file, str):
            output_file = str(output_file)
        
        # Use absolute path to avoid any path issues
        import os
        output_file = os.path.abspath(output_file)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write("TERRAFORMING MARS WINNER-ELO ANALYSIS\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Total games analyzed: {total_games}\n")
            f.write(f"Games with winner and elo_gainer: {len(winner_elo_cases)}\n")
            f.write(f"Mismatch cases (winner ≠ elo_gainer): {len(mismatch_cases)}\n")
            f.write(f"Special cases (winner with 0 gain, opponent with negative gain): {zero_gain_matches}\n")
            f.write(f"Special cases (0 gain and loss games): {zero_gain_loss_games}\n")
            f.write(f"Special cases (winner reverted games): {winner_reverted_games}\n")
            f.write(f"Special cases (Novice ELO gain: game_rank: 1, game_rank_change: 1): {novice_elo_gain_1}\n\n")
            
            # Mismatch cases
            if mismatch_cases:
                f.write("MISMATCH CASES (winner ≠ elo_gainer):\n")
                f.write("-" * 60 + "\n")
                for case in mismatch_cases:
                    # Skip winner reverted games in detailed output since they're already counted in special cases
                    if not case.get('is_winner_reverted_game', False):
                        f.write(f"replay_id: {case['replay_id']}: winner: {case['winner']}; elo_gainer: {case['elo_gainer']}, elo_gain: {case['elo_gain']}\n")
                f.write("\n")
            
            # Winner reverted games (separate section)
            if winner_reverted_cases:
                f.write("WINNER REVERTED GAMES (ELO gainer ≠ winner, but ELO loser = winner):\n")
                f.write("-" * 60 + "\n")
                for case in winner_reverted_cases:
                    f.write(f"replay_id: {case['replay_id']}: winner: {case['winner']}; elo_gainer: {case['elo_gainer']}, elo_gain: {case['elo_gain']}; elo_loser: {case['elo_loser']}, elo_loss: {case['elo_loss']}\n")
                f.write("\n")
        
        print(f"Results saved to: {output_file}")
        
    except Exception as e:
        print(f"Error saving results to file: {e}")
        print("Attempting to save to current directory...")
        
        # Fallback: try to save to current directory with a simple filename
        try:
            fallback_file = "winner_elo_analysis_fallback.txt"
            with open(fallback_file, 'w', encoding='utf-8') as f:
                f.write("TERRAFORMING MARS WINNER-ELO ANALYSIS\n")
                f.write("=" * 60 + "\n\n")
                f.write(f"Total games analyzed: {total_games}\n")
                f.write(f"Games with winner and elo_gainer: {len(winner_elo_cases)}\n")
                f.write(f"Mismatch cases (winner ≠ elo_gainer): {len(mismatch_cases)}\n")
                f.write(f"Special cases (winner with 0 gain, opponent with negative gain): {zero_gain_matches}\n")
                f.write(f"Special cases (0 gain and loss games): {zero_gain_loss_games}\n")
                f.write(f"Special cases (winner reverted games): {winner_reverted_games}\n")
                f.write(f"Special cases (Novice ELO gain: game_rank: 1, game_rank_change: 1): {novice_elo_gain_1}\n\n")
                
                if mismatch_cases:
                    f.write("MISMATCH CASES (winner ≠ elo_gainer):\n")
                    f.write("-" * 60 + "\n")
                    for case in mismatch_cases:
                        f.write(f"replay_id: {case['replay_id']}: winner: {case['winner']}; elo_gainer: {case['elo_gainer']}, elo_gain: {case['elo_gain']}\n")
                    f.write("\n")
                
                # Winner reverted games (separate section)
                if winner_reverted_cases:
                    f.write("WINNER REVERTED GAMES (ELO gainer ≠ winner, but ELO loser = winner):\n")
                    f.write("-" * 60 + "\n")
                    for case in winner_reverted_cases:
                        f.write(f"replay_id: {case['replay_id']}: winner: {case['winner']}; elo_gainer: {case['elo_gainer']}, elo_gain: {case['elo_gain']}; elo_loser: {case['elo_loser']}, elo_loss: {case['elo_loss']}\n")
                    f.write("\n")
            
            print(f"Results saved to fallback file: {fallback_file}")
            
        except Exception as fallback_error:
            print(f"Failed to save even to fallback file: {fallback_error}")
            print("Results will only be displayed in console.")

def main():
    """Main function to run the winner-ELO mismatch analysis."""
    # Parse command line arguments
    use_cache = USE_CACHE_BY_DEFAULT
    
    if len(sys.argv) > 1:
        if '--no-cache' in sys.argv:
            use_cache = False
        if '--help' in sys.argv or '-h' in sys.argv:
            print("Usage: python analyze_winner_elo_mismatch.py [--no-cache]")
            print("  --no-cache: Force reload all files (ignore cache)")
            return
    
    print("Terraforming Mars Winner-ELO Mismatch Analysis")
    print("=" * 60)
    print(f"Filtering for: {REQUIRED_MAP} map, {REQUIRED_PLAYER_COUNT} players, Colonies={'OFF' if COLONIES_MUST_BE_OFF else 'ON'}, Corporate Era={'ON' if CORPORATE_ERA_MUST_BE_ON else 'OFF'}, Draft={'ON' if DRAFT_MUST_BE_ON else 'OFF'}")
    print(f"Cache: {'Enabled' if use_cache else 'Disabled'}")
    print("=" * 60)
    
    # Initialize analyzer with path from config (reuses all the filtering and caching logic)
    analyzer = TerraformingMarsAnalyzer(DATA_DIRECTORY)
    
    # Load all games (filtering happens during loading)
    games_loaded = analyzer.load_all_games(use_cache=use_cache)
    
    if games_loaded == 0:
        print("No games found matching criteria. Please check the data directory path in config.py")
        return
    
    print(f"\nAnalyzing {games_loaded} filtered games...")
    
    # Analyze winner-ELO mismatches and zero rank changes
    total_games, winner_elo_cases, mismatch_cases, winner_reverted_cases, zero_gain_matches, zero_gain_loss_games, winner_reverted_games, novice_elo_gain_1 = analyze_winner_elo_mismatches(analyzer.games_data)
    
    # Display results
    print(f"\n" + "=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    
    print(f"\nTotal games analyzed: {games_loaded}")
    print(f"Games with winner and elo_gainer: {len(winner_elo_cases)}")
    print(f"Mismatch cases (winner ≠ elo_gainer): {len(mismatch_cases)}")
    print(f"Special cases (winner with 0 gain, opponent with negative gain): {zero_gain_matches}")
    print(f"Special cases (0 gain and loss games): {zero_gain_loss_games}")
    print(f"Special cases (winner reverted games): {winner_reverted_games}")
    print(f"Special cases (Novice ELO gain: game_rank: 1, game_rank_change: 1): {novice_elo_gain_1}")
    
    # Save results to file
    print(f"\n3. SAVING RESULTS TO FILE")
    print("-" * 60)
    save_results_to_file(total_games, winner_elo_cases, mismatch_cases, winner_reverted_cases, zero_gain_matches, zero_gain_loss_games, winner_reverted_games, novice_elo_gain_1, games_loaded)
    
    print("=" * 60)
    print("Analysis complete!")
    print("\nUsage tips:")
    print("- Use --no-cache to force reload all files")
    print("- Example: python analyze_winner_elo_mismatch.py --no-cache")
    print(f"- Results saved to: winner_elo_analysis.txt")
    print("\nConfiguration:")
    print("- Update config.py to change data directory and other settings")

if __name__ == "__main__":
    main() 