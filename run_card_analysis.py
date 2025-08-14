#!/usr/bin/env python3
"""
Script to run card analysis for multiple cards one by one.
Uses the existing CardAnalyzer and TerraformingMarsAnalyzer classes.
"""

import sys
from tm_data_analyzer import TerraformingMarsAnalyzer, display_analysis_settings

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