#!/usr/bin/env python3
"""
Script to analyze a specific game by compiling all card moves from existing game_moves_{card}.json files.
This approach is much more efficient than re-analyzing each card.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List
import glob

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

class GameAnalyzer:
    """
    Analyzer for a specific game by compiling existing card analysis data.
    """
    
    def __init__(self, analysis_output_dir: str = "analysis_output"):
        """
        Initialize the game analyzer.
        
        Args:
            analysis_output_dir: Directory containing the analysis output files
        """
        self.analysis_output_dir = Path(analysis_output_dir)
        self.game_moves_files = []
        self.game_database = {}
        self.perspective_summary = {}
        self._discover_game_moves_files()
        self._load_game_database()
        self._load_perspective_summary()
    
    def _discover_game_moves_files(self):
        """
        Discover all game_moves_{card}.json files in the analysis output directory.
        """
        pattern = self.analysis_output_dir / "game_moves_*.json"
        self.game_moves_files = list(glob.glob(str(pattern)))
        print(f"Found {len(self.game_moves_files)} game_moves files")
    
    def _load_game_database(self):
        """
        Load the game database file with all game metadata.
        """
        database_file = self.analysis_output_dir / "game_database.json"
        if database_file.exists():
            try:
                with open(database_file, 'r', encoding='utf-8') as f:
                    self.game_database = json.load(f)
                print(f"Loaded game database with {len(self.game_database)} games")
            except Exception as e:
                print(f"Error loading game database: {e}")
                self.game_database = {}
        else:
            print("⚠️  Game database file not found. Run create_game_database.py first.")
            self.game_database = {}
    
    def _load_perspective_summary(self):
        """
        Load the perspective summary to know which games have multiple perspectives.
        """
        summary_file = self.analysis_output_dir / "perspective_summary.json"
        if summary_file.exists():
            try:
                with open(summary_file, 'r', encoding='utf-8') as f:
                    self.perspective_summary = json.load(f)
                print(f"Loaded perspective summary with {len(self.perspective_summary)} games having multiple perspectives")
            except Exception as e:
                print(f"Error loading perspective summary: {e}")
                self.perspective_summary = {}
        else:
            print("⚠️  Perspective summary file not found. Run perspective_summary.py first.")
            self.perspective_summary = {}
    
    def analyze_single_game(self, replay_id: str) -> Dict[str, Any]:
        """
        Analyze a single game by compiling moves from all card analysis files.
        
        Args:
            replay_id: The replay ID of the game to analyze
            
        Returns:
            Dictionary with game analysis results
        """
        print(f"Analyzing game {replay_id}...")
        
        # Compile all moves for this game from all card files
        game_moves = self._compile_game_moves(replay_id)
        
        if not game_moves:
            return {"error": f"No moves found for game {replay_id}"}
        
        # Get game metadata from the first file that contains this game
        game_info = self._extract_game_info(replay_id)
        
        # Process moves to extract statistics
        card_analysis = self._process_game_moves(game_moves)
        
        # Compile final results
        game_analysis = {
            'game_info': game_info,
            'card_analysis': card_analysis,
            'summary': {
                'total_cards_seen': len(card_analysis),
                'cards_kept_in_starting_hand': sum(1 for card in card_analysis.values() if any(move.get('move_type') == 'draw_start' for move in card.get('moves', []))),
                'cards_drawn': sum(1 for card in card_analysis.values() if len(card.get('drawn_by_generation', {})) > 0),
                'cards_played': sum(1 for card in card_analysis.values() if card.get('played_by_generation') is not None),
                'total_moves_analyzed': sum(len(card.get('moves', [])) for card in card_analysis.values())
            }
        }
        
        return game_analysis
    
    def _compile_game_moves(self, replay_id: str) -> Dict[str, List[Dict]]:
        """
        Compile all moves for a specific game from all card analysis files.
        Now handles the new format where game_moves keys are replay_id_player_perspective.
        
        Args:
            replay_id: ID of the game to compile
            
        Returns:
            Dictionary mapping card names to their moves for this game
        """
        game_moves = {}
        
        for moves_file in self.game_moves_files:
            try:
                with open(moves_file, 'r', encoding='utf-8') as f:
                    moves_data = json.load(f)
                
                # Check if this file contains moves for our game
                # Look for keys that start with the replay_id
                matching_keys = [key for key in moves_data.keys() if key.startswith(f"{replay_id}_")]
                
                if matching_keys:
                    # Extract card name from filename
                    card_name = self._extract_card_name_from_filename(moves_file)
                    if card_name:
                        # If multiple perspectives exist, combine all moves for this card
                        all_moves_for_card = []
                        for key in matching_keys:
                            all_moves_for_card.extend(moves_data[key])
                        
                        game_moves[card_name] = all_moves_for_card
                        print(f"  Found moves for {card_name}: {len(all_moves_for_card)} moves from {len(matching_keys)} perspective(s)")
                
            except Exception as e:
                print(f"Error reading {moves_file}: {e}")
                continue
        
        return game_moves
    
    def _extract_card_name_from_filename(self, filepath: str) -> str:
        """
        Extract card name from game_moves_{card}.json filename.
        
        Args:
            filepath: Path to the moves file
            
        Returns:
            Card name extracted from filename
        """
        filename = Path(filepath).name
        if filename.startswith("game_moves_") and filename.endswith(".json"):
            # "game_moves_" is 11 characters, so start from index 11
            # Remove ".json" suffix (5 characters from the end)
            card_name = filename[11:-5]
            return card_name
        return None
    
    def _extract_game_info(self, replay_id: str) -> Dict[str, Any]:
        """
        Extract basic game information from the game database.
        Simplified to return clean game info without complex perspective handling.
        
        Args:
            replay_id: ID of the game
            
        Returns:
            Dictionary with basic game information
        """
        # Find the first database entry that matches this replay_id
        # (we'll use the perspective from the command line or default to first found)
        matching_game = None
        for game_key, game_data in self.game_database.items():
            if game_key.startswith(f"{replay_id}_"):
                matching_game = game_data
                break
        
        if matching_game:
            # Extract the basic game info
            game_info = {
                'replay_id': replay_id,
                'generations': matching_game.get('generations', 0),
                'winner': matching_game.get('winner', 'unknown'),
                'prelude_on': matching_game.get('prelude_on', False),
                'colonies_on': False,  # Not available in current database
                'corporate_era_on': False,  # Not available in current database
                'draft_on': False,  # Not available in current database
                'players': matching_game.get('players', {}),
                # Add perspective information if available
                'perspectives': len(self.perspective_summary.get(replay_id, [])) + 1 if replay_id in self.perspective_summary else 1
            }
            
            return game_info
        else:
            # Fallback if game not in database
            print(f"⚠️  Game {replay_id} not found in database")
            return {
                'replay_id': replay_id,
                'generations': 0,
                'winner': 'unknown',
                'prelude_on': False,
                'colonies_on': False,
                'corporate_era_on': False,
                'draft_on': False,
                'players': {},
                'perspectives': 0
            }
    
    def _process_game_moves(self, game_moves: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """
        Process moves for all cards in a game to extract statistics.
        Optimized to process all moves in a single pass.
        
        Args:
            game_moves: Dictionary mapping card names to their moves
            
        Returns:
            Dictionary mapping card names to their processed statistics
        """
        card_analysis = {}
        
        # Process all moves in a single pass
        for card_name, moves in game_moves.items():
            # Initialize statistics for this card
            card_stats = {
                'drawn_by_generation': {},
                'played_by_generation': None,  # Single value since cards can only be played once
                'paid': None,  # Cost paid when played (only relevant if played)
                'seen_by_generation': {},  # Track when card is seen by generation
                'draw_methods': {},
                'seen_methods': {},  # Only actual "seen" methods, not all move types
                'moves': []
            }
            
            # Process each move for this card
            for move in moves:
                move_type = move.get('move_type', '')
                generation = move.get('generation', 0)
                
                # Track draws
                if move_type.startswith('draw'):
                    card_stats['drawn_by_generation'][generation] = card_stats['drawn_by_generation'].get(generation, 0) + 1
                    
                    # Track draw methods
                    if move_type in card_stats['draw_methods']:
                        card_stats['draw_methods'][move_type] += 1
                    else:
                        card_stats['draw_methods'][move_type] = 1
                
                # Track plays (cards can only be played once)
                if move_type == 'play':
                    card_stats['played_by_generation'] = generation  # Single value
                    card_stats['paid'] = move.get('paid') # Store paid information
                
                # Track when card is "seen" (draft, reveal, etc.)
                # Only count actual "seen" methods, not activations or other actions
                if move_type in ['draft_1', 'draft_2', 'draft_3', 'draft_4', 'reveal_microbe', 'reveal_plant', 'reveal_space']:
                    # Track seen methods
                    if move_type in card_stats['seen_methods']:
                        card_stats['seen_methods'][move_type] += 1
                    else:
                        card_stats['seen_methods'][move_type] = 1
                    
                    # Track seen by generation
                    card_stats['seen_by_generation'][generation] = card_stats['seen_by_generation'].get(generation, 0) + 1
                
                # Store the move details
                card_stats['moves'].append({
                    'description': move.get('description', ''),
                    'generation': generation,
                    'move_number': move.get('move_number', 0),
                    'action_type': move.get('action_type', ''),
                    'move_type': move_type
                })
            
            # Store the processed card statistics
            card_analysis[card_name] = card_stats
        
        return card_analysis
    
    def analyze_multiple_games(self, replay_ids: List[str]) -> Dict[str, Any]:
        """
        Analyze multiple games and create a summary.
        
        Args:
            replay_ids: List of replay IDs to analyze
            
        Returns:
            Dictionary with analysis results for all games
        """
        print(f"Analyzing {len(replay_ids)} games...")
        
        all_games_analysis = {}
        successful_analyses = 0
        failed_analyses = 0
        
        for i, replay_id in enumerate(replay_ids, 1):
            print(f"\n[{i}/{len(replay_ids)}] Analyzing game: {replay_id}")
            
            try:
                game_analysis = self.analyze_single_game(replay_id)
                
                if 'error' not in game_analysis:
                    all_games_analysis[replay_id] = game_analysis
                    successful_analyses += 1
                else:
                    print(f"  ❌ Error: {game_analysis['error']}")
                    failed_analyses += 1
                    
            except Exception as e:
                print(f"  ❌ Exception: {e}")
                failed_analyses += 1
        
        # Create summary
        summary = {
            'total_games_requested': len(replay_ids),
            'successful_analyses': successful_analyses,
            'failed_analyses': failed_analyses,
            'games_analyzed': list(all_games_analysis.keys())
        }
        
        return {
            'summary': summary,
            'games_analysis': all_games_analysis
        }

def load_game_list(file_path: str = "game_list.txt") -> list:
    """
    Load the game list from the specified file.
    
    Args:
        file_path: Path to the game list file
        
    Returns:
        List of game replay IDs
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            # Evaluate the content as a Python literal (safe since we control the file)
            game_list = eval(content)
            return game_list
    except FileNotFoundError:
        print(f"Error: Game list file '{file_path}' not found.")
        return []
    except Exception as e:
        print(f"Error loading game list: {e}")
        return []

def save_game_analysis(game_analysis: Dict[str, Any], replay_id: str, output_dir: str = "analysis_output"):
    """
    Save game analysis to JSON file.
    
    Args:
        game_analysis: Game analysis results
        replay_id: ID of the analyzed game (may include perspective like "123456_789")
        output_dir: Directory to save output files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create game analysis subfolder
    game_analysis_path = output_path / "game_analysis"
    game_analysis_path.mkdir(exist_ok=True)
    
    # Save main analysis
    filename = f"game_analysis_{replay_id}.json"
    with open(game_analysis_path / filename, 'w', encoding='utf-8') as f:
        json.dump(game_analysis, f, indent=2, default=str)
    
    # Show file size
    file_path = game_analysis_path / filename
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"Game analysis saved to: {game_analysis_path}/{filename} (size: {file_size_mb:.1f} MB)")
    
    return file_path

def save_multiple_games_analysis(games_analysis: Dict[str, Any], output_dir: str = "analysis_output"):
    """
    Save multiple games analysis to JSON file.
    
    Args:
        games_analysis: Analysis results for multiple games
        output_dir: Directory to save output files
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Create game analysis subfolder
    game_analysis_path = output_path / "game_analysis"
    game_analysis_path.mkdir(exist_ok=True)
    
    # Save main analysis
    filename = f"multiple_games_analysis.json"
    with open(game_analysis_path / filename, 'w', encoding='utf-8') as f:
        json.dump(games_analysis, f, indent=2, default=str)
    
    # Show file size
    file_path = game_analysis_path / filename
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"Multiple games analysis saved to: {game_analysis_path}/{filename} (size: {file_size_mb:.1f} MB)")
    
    return file_path

def main():
    """
    Main function to run game analysis.
    """
    
    # Parse command line arguments
    replay_id = None
    games_to_analyze = []
    
    if len(sys.argv) > 1:
        if '--replay' in sys.argv:
            replay_index = sys.argv.index('--replay')
            if len(sys.argv) > replay_index + 1:
                replay_id = sys.argv[replay_index + 1]
                games_to_analyze = [replay_id]
        if '--games' in sys.argv:
            # Allow user to specify custom games
            games_index = sys.argv.index('--games')
            if len(sys.argv) > games_index + 1:
                custom_games = sys.argv[games_index + 1].split(',')
                games_to_analyze = [game.strip() for game in custom_games]
    
    # If no specific games specified, try to load from file
    if not games_to_analyze:
        games_to_analyze = load_game_list()
        if not games_to_analyze:
            print("❌ Please specify games to analyze using one of:")
            print("   --replay <replay_id> for a single game")
            print("   --games 'id1,id2,id3' for multiple games")
            print("   Create a 'game_list.txt' file with game IDs")
            print("Example: python game_analyzer.py --replay 123456789")
            print("Example: python game_analyzer.py --games '123456789,987654321'")
            return
    
    print("Starting Game Analysis by Compiling Existing Card Data")
    print("=" * 60)
    
    if len(games_to_analyze) == 1:
        print(f"Game to analyze: {games_to_analyze[0]}")
    else:
        print(f"Games to analyze: {len(games_to_analyze)}")
    
    print("=" * 60)
    
    # Create game analyzer
    game_analyzer = GameAnalyzer()
    
    # Check if game database is loaded
    if not game_analyzer.game_database:
        print("❌ Game database not found!")
        print("Please run create_game_database.py first to create the game database.")
        print("This script needs the game_database.json file to work properly.")
        return
    
    # Analyze games
    if len(games_to_analyze) == 1:
        # Single game analysis
        replay_id = games_to_analyze[0]
        
        # Check if this game has multiple perspectives in the database
        if replay_id in game_analyzer.perspective_summary:
            # Multiple perspectives - analyze each separately
            perspectives = game_analyzer.perspective_summary[replay_id]
            print(f"📊 Game {replay_id} has {len(perspectives)} perspectives: {perspectives}")
            
            for i, player_perspective in enumerate(perspectives, 1):
                print(f"\n[{i}/{len(perspectives)}] Analyzing perspective: {player_perspective}")
                
                # Analyze the game from this perspective
                game_analysis = game_analyzer.analyze_single_game(replay_id)
                
                if 'error' in game_analysis:
                    print(f"  ❌ Error: {game_analysis['error']}")
                    continue
                
                # Save results with perspective in filename
                output_file = save_game_analysis(game_analysis, f"{replay_id}_{player_perspective}")
                
                # Display summary
                summary = game_analysis['summary']
                print(f"  ✅ Perspective analysis complete!")
                print(f"  📊 Summary:")
                print(f"     Total cards seen: {summary['total_cards_seen']}")
                print(f"     Cards kept in starting hand: {summary['cards_kept_in_starting_hand']}")
                print(f"     Cards drawn: {summary['cards_drawn']}")
                print(f"     Cards played: {summary['cards_played']}")
                print(f"     Total moves analyzed: {summary['total_moves_analyzed']}")
                print(f"  📁 Results saved to: {output_file}")
            
            print(f"\n✅ All perspectives analyzed for game {replay_id}!")
            
        else:
            # Single perspective - analyze normally
            print(f"📊 Game {replay_id} has single perspective, analyzing normally...")
            
            # Analyze the game
            game_analysis = game_analyzer.analyze_single_game(replay_id)
            
            if 'error' in game_analysis:
                print(f"❌ Error: {game_analysis['error']}")
                return
            
            # Save results
            output_file = save_game_analysis(game_analysis, replay_id)
            
            # Display summary
            summary = game_analysis['summary']
            print(f"\n✅ Game analysis complete!")
            print(f"📊 Summary:")
            print(f"   Total cards seen: {summary['total_cards_seen']}")
            print(f"   Cards kept in starting hand: {summary['cards_kept_in_starting_hand']}")
            print(f"   Cards drawn: {summary['cards_drawn']}")
            print(f"   Cards played: {summary['cards_played']}")
            print(f"   Total moves analyzed: {summary['total_moves_analyzed']}")
            
            print(f"\n📁 Results saved to: {output_file}")
    
    else:
        # Multiple games analysis
        print(f"\nStarting analysis of {len(games_to_analyze)} games...")
        print("-" * 60)
        
        # Analyze multiple games
        games_analysis = game_analyzer.analyze_multiple_games(games_to_analyze)
        
        # Save results
        output_file = save_multiple_games_analysis(games_analysis)
        
        # Display summary
        summary = games_analysis['summary']
        print(f"\n✅ Multiple games analysis complete!")
        print(f"📊 Summary:")
        print(f"   Total games requested: {summary['total_games_requested']}")
        print(f"   Successful analyses: {summary['successful_analyses']}")
        print(f"   Failed analyses: {summary['failed_analyses']}")
        
        print(f"\n📁 Results saved to: {output_file}")
    
    print("\nUsage tips:")
    print("- Use --replay <replay_id> to analyze a single game")
    print("- Use --games 'id1,id2,id3' to analyze multiple games")
    print("- Create 'game_list.txt' file with game IDs for batch processing")
    print("- This tool reads existing game_moves_{card}.json files")
    print("- Requires game_database.json (run create_game_database.py first)")
    print("- Example: python game_analyzer.py --replay 123456789")
    print("- Example: python game_analyzer.py --games '123456789,987654321'")

if __name__ == "__main__":
    main() 