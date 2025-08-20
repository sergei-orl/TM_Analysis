#!/usr/bin/env python3
"""
Script to run card analysis for multiple cards one by one.
Uses the existing CardAnalyzer and TerraformingMarsAnalyzer classes.
"""

import sys
import json
from pathlib import Path
from tm_data_analyzer import TerraformingMarsAnalyzer, display_analysis_settings
from tqdm import tqdm

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

def load_card_list(file_path: str = "card_list.txt") -> list:
    """
    Load the card list from the specified file.
    
    Args:
        file_path: Path to the card list file
        
    Returns:
        List of card names
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Evaluate the content as a Python literal (safe since we control the file)
            card_list = eval(content)
            return card_list
    except FileNotFoundError:
        print(f"Error: Card list file '{file_path}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error loading card list: {e}")
        sys.exit(1)

def calculate_relative_performance_metrics(analyzer, analysis_dir: str = "analysis_output"):
    """
    Calculate relative performance metrics for all analyzed cards.
    
    This function:
    1. Uses the analyzer's games data to calculate overall baseline metrics
    2. Loads all card analysis files
    3. Computes relative performance metrics for each card using the overall baseline
    4. Saves updated analysis files with the new metrics
    
    Args:
        analyzer: TerraformingMarsAnalyzer instance with loaded games data
        analysis_dir: Directory containing card analysis files
        
    Returns:
        Dictionary with baseline metrics and summary
    """
    analysis_path = Path(analysis_dir)
    if not analysis_path.exists():
        print(f"❌ Analysis directory '{analysis_dir}' not found!")
        return {}
    
    # Find all card analysis files
    card_files = list(analysis_path.glob("card_analysis_*.json"))
    if not card_files:
        print(f"❌ No card analysis files found in '{analysis_dir}'!")
        return {}
    
    print(f"\n📊 Calculating relative performance metrics for {len(card_files)} cards...")
    
    # Calculate overall baseline from ALL games in the dataset (not filtered by card context)
    print("\n📈 Calculating overall baseline metrics from all games...")
    
    total_games = len(analyzer.games_data)
    if total_games == 0:
        print("❌ No games data available for baseline calculation!")
        return {}
    
    # Initialize baseline calculation
    total_player_perspective_games = 0  # Total games where player_perspective participated
    total_player_perspective_wins = 0   # Total wins by player_perspective
    total_elo_gains = 0
    valid_elo_games = 0
    
    # Calculate baseline from ALL games
    for game in tqdm(analyzer.games_data, desc="Calculating baseline", unit="game"):
        players = game.get('players', {})
        winner = game.get('winner', 'unknown')
        player_perspective = game.get('player_perspective', '')
        
        # Only count this game if it has a valid player_perspective
        if not player_perspective:
            continue
            
        # Get the player_perspective player data
        player_perspective_data = players.get(player_perspective)
        if not player_perspective_data or not isinstance(player_perspective_data, dict):
            continue
            
        player_perspective_name = player_perspective_data.get('player_name', 'unknown')
        if player_perspective_name == 'unknown':
            continue
        
        # Count this game for the player_perspective
        total_player_perspective_games += 1
        
        # Check if this player_perspective won
        if player_perspective_name == winner:
            total_player_perspective_wins += 1
        
        # Get ELO gain for this player_perspective
        elo_data = player_perspective_data.get('elo_data')
        if elo_data and isinstance(elo_data, dict):
            game_rank_change = elo_data.get('game_rank_change', 0)
            if game_rank_change is not None and isinstance(game_rank_change, (int, float)):
                total_elo_gains += game_rank_change
                valid_elo_games += 1
    
    # Calculate overall baseline
    overall_baseline = {
        'win_rate': (total_player_perspective_wins / total_player_perspective_games) * 100 if total_player_perspective_games > 0 else 0,
        'elo_gain': total_elo_gains / valid_elo_games if valid_elo_games > 0 else 0
    }
    
    print(f"📊 Overall baseline calculated from {total_games} games:")
    print(f"  Total player_perspective games: {total_player_perspective_games}")
    print(f"  Total player_perspective wins: {total_player_perspective_wins}")
    print(f"  Overall win rate: {overall_baseline['win_rate']:.2f}%")
    print(f"  Total ELO gains: {total_elo_gains}")
    print(f"  Valid ELO games: {valid_elo_games}")
    print(f"  Overall ELO gain: {overall_baseline['elo_gain']:.4f}")
    
    # Load all card analyses
    all_cards_data = {}
    for card_file in card_files:
        try:
            with open(card_file, 'r', encoding='utf-8') as f:
                card_data = json.load(f)
            
            card_name = card_data.get('card_name', 'Unknown')
            all_cards_data[card_name] = card_data
                
        except Exception as e:
            print(f"❌ Error loading {card_file.name}: {e}")
            continue
    
    # Calculate relative performance metrics for each card
    print("\n🔄 Calculating relative performance metrics...")
    
    for card_name, card_data in all_cards_data.items():
        # Initialize relative metrics section
        if 'relative_performance' not in card_data:
            card_data['relative_performance'] = {}
        
        win_rate_by_case = card_data.get('win_rate_by_case', {})
        elo_metrics_by_case = card_data.get('elo_metrics_by_case', {})
        
        # Calculate relative win rates (5% = 100 points) using overall baseline
        for case in ['when_seen', 'when_drawn', 'when_bought_during_game', 'when_played']:
            relative_key = f'relative_win_rate_{case}'
            
            if case in win_rate_by_case:
                win_rate = win_rate_by_case[case]
                difference = win_rate - overall_baseline['win_rate']
                # Convert to relative scale: 5% = 100 points
                relative_value = (difference / 5.0) * 100
                card_data['relative_performance'][relative_key] = round(relative_value, 2)
            else:
                card_data['relative_performance'][relative_key] = 0
        
        # Calculate relative ELO gains (1 ELO point = 100 points) using overall baseline
        for case in ['when_seen', 'when_drawn', 'when_bought_during_game', 'when_played']:
            relative_key = f'relative_elo_gain_{case}'
            
            if case in elo_metrics_by_case:
                elo_gain = elo_metrics_by_case[case]['average_elo_gain']
                difference = elo_gain - overall_baseline['elo_gain']
                # Convert to relative scale: 1 ELO point = 100 points
                relative_value = difference * 100
                card_data['relative_performance'][relative_key] = round(relative_value, 2)
            else:
                card_data['relative_performance'][relative_key] = 0
        
        # Apply Bayesian averaging to stabilize metrics when game counts vary
        # Only apply to the 4 cases that have varying game sizes
        bayesian_cases = ['when_bought_during_game', 'when_played']
        K = 200  # Bayesian prior strength
        
        for case in bayesian_cases:
            if case in win_rate_by_case and case in elo_metrics_by_case:
                # Get current values
                current_win_rate = win_rate_by_case[case]
                current_elo_gain = elo_metrics_by_case[case]['average_elo_gain']
                
                # Get game count for this case from win rate data
                win_count = card_data.get('win_count_by_case', {}).get(case, 0)
                if current_win_rate > 0:
                    game_count = int((win_count / current_win_rate) * 100)
                else:
                    game_count = 0
                
                # Apply Bayesian averaging: (x̄·n + μ·K) / (n + K)
                # where x̄ = current average, n = game count, μ = overall baseline, K = prior strength
                if game_count > 0:
                    # Bayesian average for win rate
                    bayesian_win_rate = (current_win_rate * game_count + overall_baseline['win_rate'] * K) / (game_count + K)
                    
                    # Bayesian average for ELO gain
                    bayesian_elo_gain = (current_elo_gain * game_count + overall_baseline['elo_gain'] * K) / (game_count + K)
                    
                    # Update the main metrics with Bayesian averages
                    card_data['win_rate_by_case'][case] = round(bayesian_win_rate, 4)
                    card_data['elo_metrics_by_case'][case]['average_elo_gain'] = round(bayesian_elo_gain, 4)
                    
                    # Add Bayesian averaging info to relative performance
                    card_data['relative_performance'][f'bayesian_win_rate_{case}'] = round(bayesian_win_rate, 4)
                    card_data['relative_performance'][f'bayesian_elo_gain_{case}'] = round(bayesian_elo_gain, 4)
                    card_data['relative_performance'][f'original_win_rate_{case}'] = round(current_win_rate, 4)
                    card_data['relative_performance'][f'original_elo_gain_{case}'] = round(current_elo_gain, 4)
                    card_data['relative_performance'][f'game_count_{case}'] = game_count
                    card_data['relative_performance'][f'bayesian_prior_strength'] = K
        
        # Save updated card analysis
        try:
            card_filename = f"card_analysis_{card_name.replace(' ', '_').replace('"', '')}.json"
            card_file_path = analysis_path / card_filename
            
            with open(card_file_path, 'w', encoding='utf-8') as f:
                json.dump(card_data, f, indent=2, default=str)
                
        except Exception as e:
            print(f"❌ Error saving updated analysis for {card_name}: {e}")
    
    # Create summary of relative performance metrics
    summary = {
        'overall_baseline': overall_baseline,
        'total_games_analyzed': total_games,
        'total_player_games': total_player_perspective_games,
        'total_player_wins': total_player_perspective_wins,
        'total_cards_processed': len(all_cards_data),
        'relative_metrics_explanation': {
            'win_rate_scale': '5% difference = 100 points (positive = above average, negative = below average)',
            'elo_gain_scale': '1 ELO point difference = 100 points (positive = above average, negative = below average)',
            'interpretation': 'Positive values indicate above-average performance, negative values indicate below-average performance',
            'baseline_source': f'Calculated from {total_games} total games in dataset (all filtering and correction done during data loading)',
            'win_rate_calculation': f'Win rate = (total wins / total player games) * 100 = ({total_player_perspective_wins} / {total_player_perspective_games}) * 100',
            'bayesian_averaging': 'Both win rates and ELO gains use Bayesian averaging with K=200 prior strength to stabilize metrics when game counts vary significantly',
            'bayesian_formula': 'Bayesian average = (current_avg × game_count + prior_avg × K) / (game_count + K) where K=200'
        }
    }
    
    # Save baseline summary
    baseline_file_path = analysis_path / "overall_baseline_summary.json"
    try:
        with open(baseline_file_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"\n✅ Overall baseline summary saved to: {baseline_file_path}")
    except Exception as e:
        print(f"❌ Error saving baseline summary: {e}")
    
    print(f"\n✅ Relative performance metrics calculated and saved for {len(all_cards_data)} cards!")
    print("📁 Updated analysis files now include 'relative_performance' section")
    print("🎯 All metrics compared to the same overall baseline from all games")
    print("🔧 All filtering, correction, and duplicate removal done during data loading")
    print("📊 Win rates and ELO gains stabilized with Bayesian averaging (K=200) for varying game counts")
    
    return summary

def main():
    """
    Main function to run card analysis for multiple cards.
    """
    
    # Load cards from the card list file
    cards_to_analyze = load_card_list()
    
    # Parse command line arguments
    use_cache = USE_CACHE_BY_DEFAULT
    
    if len(sys.argv) > 1:
        if '--no-cache' in sys.argv:
            use_cache = False
        if '--cards' in sys.argv:
            # Allow user to specify custom cards
            cards_index = sys.argv.index('--cards')
            if len(sys.argv) > cards_index + 1:
                custom_cards = sys.argv[cards_index + 1].split(',')
                cards_to_analyze = [card.strip() for card in custom_cards]
    
    # Display analysis settings using shared function
    display_analysis_settings(use_cache=use_cache)
    print(f"Cards to analyze: {len(cards_to_analyze)}")
    print("=" * 60)
    
    analyzer = TerraformingMarsAnalyzer(DATA_DIRECTORY)
    
    # Use shared function to analyze multiple cards
    successful_analyses, failed_analyses = analyzer.analyze_multiple_cards(cards_to_analyze, use_cache)
    
    # Check if any analysis was performed
    if successful_analyses == 0 and failed_analyses == 0:
        print("\n❌ No games loaded. Analysis could not proceed.")
        return
    
    # Summary
    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Total cards processed: {len(cards_to_analyze)}")
    print(f"Successful analyses: {successful_analyses}")
    print(f"Failed analyses: {failed_analyses}")
    print(f"Results saved to: analysis_output/")
    
    if successful_analyses > 0:
        print(f"\n✅ Successfully analyzed {successful_analyses} cards!")
        
        # Calculate relative performance metrics for all analyzed cards
        print("\n" + "=" * 60)
        print("CALCULATING RELATIVE PERFORMANCE METRICS")
        print("=" * 60)
        
        try:
            baseline_summary = calculate_relative_performance_metrics(analyzer)
            if baseline_summary:
                print(f"\n📊 Overall baseline calculated from {baseline_summary['total_games_analyzed']} total games")
                print(f"🎯 Relative performance metrics added to {baseline_summary['total_cards_processed']} cards")
                print("📋 All metrics compared to the same overall baseline (not filtered by card context)")
        except Exception as e:
            print(f"❌ Error calculating relative performance metrics: {e}")
    
    if failed_analyses > 0:
        print(f"❌ Failed to analyze {failed_analyses} cards")
    
    print("\nUsage tips:")
    print("- Use --no-cache to force reload all files")
    print("- Use --cards 'Card1,Card2,Card3' to specify custom cards")
    print("- Example: python run_card_analysis.py --cards 'Cloud Seeding,Lunar Beam'")
    print("- Cards are loaded from 'card_list.txt' by default")
    print("- Custom cards override the file list when specified")
    print("\nConfiguration:")
    print("- Update config.py to change data directory and other settings")
    print("\nNew Features:")
    print("- Relative performance metrics automatically calculated after analysis")
    print("- Overall baseline calculated from ALL games in dataset")
    print("- Each card analysis now includes 'relative_performance' section")
    print("- All metrics compared to the same overall baseline")

if __name__ == "__main__":
    main() 