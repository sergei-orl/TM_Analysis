#!/usr/bin/env python3
"""
Script to run card analysis for multiple cards one by one.
Uses the existing CardAnalyzer and TerraformingMarsAnalyzer classes.
"""

import sys
import time
from tm_data_analyzer import TerraformingMarsAnalyzer
from card_analyzer import CardAnalyzer

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
    
    # Initialize analyzer with path from config
    print("Starting Terraforming Mars Multi-Card Analysis")
    print("=" * 60)
    print(f"Filtering for: {REQUIRED_MAP} map, {REQUIRED_PLAYER_COUNT} players, Colonies={'OFF' if COLONIES_MUST_BE_OFF else 'ON'}, Corporate Era={'ON' if CORPORATE_ERA_MUST_BE_ON else 'OFF'}, Draft={'ON' if DRAFT_MUST_BE_ON else 'OFF'}")
    print(f"Cache: {'Enabled' if use_cache else 'Disabled'}")
    print(f"Cards to analyze: {len(cards_to_analyze)}")
    print("=" * 60)
    
    analyzer = TerraformingMarsAnalyzer(DATA_DIRECTORY)
    
    # Load all games (filtering happens during loading)
    print("\nLoading games data...")
    games_loaded = analyzer.load_all_games(use_cache=use_cache)
    
    if games_loaded == 0:
        print("No games found matching criteria. Please check the data directory path in config.py")
        return
    
    print(f"✅ Loaded {games_loaded} filtered games")
    
    # Analyze each card one by one
    print(f"\nStarting analysis of {len(cards_to_analyze)} cards...")
    print("-" * 60)
    
    successful_analyses = 0
    failed_analyses = 0
    
    for i, card_name in enumerate(cards_to_analyze, 1):
        print(f"\n[{i}/{len(cards_to_analyze)}] {time.strftime('%H:%M:%S')} Analyzing card: '{card_name}'")
        
        try:
            # Create a new CardAnalyzer instance for each card to ensure clean state
            card_analyzer = CardAnalyzer(analyzer.games_data)
            
            # Analyze the card
            card_stats = card_analyzer.save_card_analysis(card_name)
            
            if card_stats['total_games_analyzed'] > 0:
                print(f"✅ Successfully analyzed '{card_name}': {card_stats['total_games_analyzed']} games")
                successful_analyses += 1
            else:
                print(f"⚠️  No games found for card: '{card_name}'")
                failed_analyses += 1
                
        except Exception as e:
            print(f"❌ Error analyzing '{card_name}': {e}")
            failed_analyses += 1
        
        # Add a small delay between analyses to avoid overwhelming the system
        if i < len(cards_to_analyze):
            print("Waiting 0.5 seconds before next analysis...")
            time.sleep(0.5)
    
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

if __name__ == "__main__":
    main() 