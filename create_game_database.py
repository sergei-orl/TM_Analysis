#!/usr/bin/env python3
"""
Script to create a condensed game database with all necessary metadata.
This creates a single JSON file that can be used later for game analysis.
Uses the existing TerraformingMarsAnalyzer infrastructure.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

# Import the existing analyzer infrastructure
from tm_data_analyzer import TerraformingMarsAnalyzer, display_analysis_settings

class GameDatabaseCreator:
    """
    Creates a condensed database of all games with necessary metadata.
    Uses the existing TerraformingMarsAnalyzer infrastructure.
    """
    
    def __init__(self, data_directory: str):
        """
        Initialize the database creator.
        
        Args:
            data_directory: Path to the directory containing game JSON files
        """
        self.data_directory = data_directory
        self.analyzer = TerraformingMarsAnalyzer(data_directory)
        self.game_database = {}
        
    def load_all_games(self, use_cache: bool = True) -> int:
        """
        Load all games using the existing TerraformingMarsAnalyzer infrastructure.
        
        Args:
            use_cache: Whether to use cache for faster loading
            
        Returns:
            Number of games loaded
        """
        print(f"Loading games using existing infrastructure...")
        
        # Use the existing analyzer to load games with all the filtering logic
        games_loaded = self.analyzer.load_all_games(use_cache=use_cache)
        
        if games_loaded == 0:
            print("❌ No games found matching criteria. Please check the data directory path in config.py")
            return 0
        
        print(f"✅ Loaded {games_loaded} filtered games using existing infrastructure")
        return games_loaded
    
    def create_game_database(self) -> Dict[str, Any]:
        """
        Create the condensed game database with all necessary metadata.
        
        Returns:
            Dictionary containing the game database
        """
        print(f"\nCreating game database from {len(self.analyzer.games_data)} games...")
        
        # Track statistics
        total_games = len(self.analyzer.games_data)
        processed_games = 0
        duplicate_games = 0
        
        # Initialize correction counters and tracking lists
        self._corrected_perspective_count = 0
        self._corrected_winners_count = 0
        self._corrected_perspective_ids = []
        self._corrected_winners_ids = []
        self._perspective_corrections = {}  # Track original -> corrected mappings
        
        # Process each game
        for game in self.analyzer.games_data:
            
            # Extract and process game data (this will correct perspective if needed)
            game_entry = self._extract_game_data(game)
            if game_entry:
                # Check for duplicate games AFTER perspective correction
                # This prevents duplicates from the same replay_id + corrected_perspective combination
                if self._check_and_track_duplicate_game(game_entry['replay_id'], game_entry['player_perspective']):
                    duplicate_games += 1
                    continue
                
                processed_games += 1
                game_key = f"{game_entry['replay_id']}_{game_entry['player_perspective']}"
                self.game_database[game_key] = game_entry
        
        # Final verification
        total_accounted_for = processed_games + duplicate_games
        if total_accounted_for != total_games:
            print(f"⚠️  WARNING: Total accounted for ({total_accounted_for}) doesn't match total games ({total_games})")
            print(f"   Missing: {total_games - total_accounted_for} games")
        
        print(f"✅ Game database creation complete!")
        print(f"📊 Summary:")
        print(f"   Total games loaded: {total_games}")
        print(f"   Processed games: {processed_games}")
        print(f"   Duplicate games discarded: {duplicate_games}")
        print(f"   Player perspective corrected: {self._corrected_perspective_count}")
        print(f"   Winners corrected: {self._corrected_winners_count}")
        print(f"   Final unique games in database: {len(self.game_database)}")
        
        # Show some examples of corrections
        if self._corrected_perspective_ids:
            print(f"   Sample perspective corrections: {self._corrected_perspective_ids[:5]}")
        if self._corrected_winners_ids:
            print(f"   Sample winner corrections: {self._corrected_winners_ids[:5]}")
        
        # Final verification
        expected_unique = total_games - duplicate_games
        if len(self.game_database) != expected_unique:
            print(f"⚠️  WARNING: Database count ({len(self.game_database)}) doesn't match expected ({expected_unique})")
        else:
            print(f"✅ Database count matches expected: {len(self.game_database)} = {total_games} - {duplicate_games}")
        
        return self.game_database
    
    def _check_and_track_duplicate_game(self, replay_id: str, player_perspective: str) -> bool:
        """
        Check if a game has already been processed and track it if it's a duplicate.
        
        Args:
            replay_id: The replay ID of the game
            player_perspective: The original player perspective ID
            
        Returns:
            True if this is a duplicate game, False otherwise
        """
        game_key = f"{replay_id}_{player_perspective}"
        
        if hasattr(self, '_processed_games') and game_key in self._processed_games:
            return True
        else:
            # Mark this game as processed
            if not hasattr(self, '_processed_games'):
                self._processed_games = set()
            self._processed_games.add(game_key)
            return False
    
    def _extract_game_data(self, game: Dict) -> Dict[str, Any]:
        """
        Extract all necessary data from a game.
        
        Args:
            game: Game data dictionary
            
        Returns:
            Condensed game data dictionary
        """
        replay_id = game.get('replay_id', '')
        player_perspective = game.get('player_perspective', '')
        moves = game.get('moves', [])
        
        # Correct player perspective if needed
        corrected_perspective, was_corrected = self._correct_player_perspective(moves, player_perspective)
        if was_corrected:
            player_perspective = corrected_perspective
            # Update the global counter and tracking
            self._corrected_perspective_count += 1
            self._corrected_perspective_ids.append(replay_id)
            self._perspective_corrections[replay_id] = {
                'original': game.get('player_perspective', ''),
                'corrected': corrected_perspective
            }
        
        # Extract basic game info
        game_entry = {
            'replay_id': replay_id,
            'player_perspective': player_perspective,
            'winner': game.get('winner', 'unknown'),
            'generations': game.get('generations', 0),
            'prelude_on': game.get('prelude_on', False),
            'game_date': game.get('game_date', 'unknown'),
            'starting_hand': False,  # Will be set below
            'players': {}
        }
        
        # Check if any player has starting_hand data
        players = game.get('players', {})
        has_starting_hand = False
        for player_data in players.values():
            if isinstance(player_data, dict) and 'starting_hand' in player_data:
                has_starting_hand = True
                break
        
        game_entry['starting_hand'] = has_starting_hand
        
        # Extract player data
        players = game.get('players', {})
        for player_id, player_data in players.items():
            if not isinstance(player_data, dict):
                continue
            
            # Basic player info
            player_info = {
                'player_name': player_data.get('player_name', 'unknown'),
                'corporation': player_data.get('corporation', 'unknown'),
                'final_vp': player_data.get('final_vp', 0),
                'final_tr': player_data.get('final_tr', 0),
                'elo_data': {}
            }
            
            # ELO data
            elo_data = player_data.get('elo_data', {})
            if elo_data and isinstance(elo_data, dict):
                player_info['elo_data'] = {
                    'elo': elo_data.get('game_rank', 0),
                    'elo_change': elo_data.get('game_rank_change', 0)
                }
            
            game_entry['players'][player_id] = player_info
        
        # Determine actual winner and correct if needed
        corrected_winner = self._determine_actual_winner(game_entry, players)
        if corrected_winner != game_entry['winner']:
            game_entry['winner'] = corrected_winner
            # Update the global counter and tracking
            self._corrected_winners_count += 1
            self._corrected_winners_ids.append(replay_id)
        
        return game_entry
    
    def _correct_player_perspective(self, moves: List[Dict], original_player_perspective: str) -> tuple[str, bool]:
        """
        Detect and correct player perspective based on "You choose corporation" move.
        This is copied from card_analyzer.py
        
        Args:
            moves: List of moves for the game
            original_player_perspective: Original player perspective ID
            
        Returns:
            Tuple of (corrected_player_perspective, was_corrected)
        """
        for move in moves:
            if not isinstance(move, dict):
                continue
            
            description = move.get('description', '')
            player_id = move.get('player_id', '')
            
            if "You choose corporation" in description:
                if player_id != original_player_perspective:
                    return player_id, True
                else:
                    return original_player_perspective, False
        
        # No "You choose corporation" found, keep original
        return original_player_perspective, False
    
    def _determine_actual_winner(self, game_entry: Dict, players: Dict) -> str:
        """
        Determine the actual winner based on ELO data.
        This is based on the logic from _analyze_player_performance in card_analyzer.py
        
        Args:
            game_entry: The game entry being processed
            players: Players data from the game
            
        Returns:
            The corrected winner name
        """
        winner = game_entry['winner']
        
        # Find elo_gainer and elo_loser
        elo_gainer = 'unknown'
        elo_loser = 'unknown'
        
        for _, player_data in players.items():
            if not isinstance(player_data, dict):
                continue
                
            player_name = player_data.get('player_name', 'unknown')
            elo_data = player_data.get('elo_data')
            
            if elo_data and isinstance(elo_data, dict):
                game_rank_change = elo_data.get('game_rank_change', 0)
                if isinstance(game_rank_change, (int, float)):
                    if game_rank_change > 0:
                        elo_gainer = player_name
                    elif game_rank_change < 0:
                        elo_loser = player_name
        
        # Correct winner if needed: if elo_gainer != winner and elo_loser == winner, rewrite winner
        if elo_gainer != 'unknown' and elo_gainer != winner and elo_loser == winner:
            return elo_gainer
        
        return winner

def save_game_database(game_database: Dict[str, Any], output_dir: str = "analysis_output"):
    """
    Save the game database to a JSON file.
    
    Args:
        game_database: The game database dictionary
        output_dir: Directory to save the database file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save database
    filename = "game_database.json"
    file_path = output_path / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(game_database, f, indent=2, default=str)
    
    # Show file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"\n📁 Game database saved to: {file_path} (size: {file_size_mb:.1f} MB)")
    
    return file_path

def save_corrections_file(corrections_data: Dict[str, Any], output_dir: str = "analysis_output"):
    """
    Save the corrections data to a separate JSON file.
    
    Args:
        corrections_data: Dictionary containing correction information
        output_dir: Directory to save the corrections file
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Save corrections
    filename = "game_corrections.json"
    file_path = output_path / filename
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(corrections_data, f, indent=2, default=str)
    
    # Show file size
    file_size_mb = file_path.stat().st_size / (1024 * 1024)
    print(f"📁 Corrections file saved to: {file_path} (size: {file_size_mb:.1f} MB)")
    
    return file_path

def main():
    """
    Main function to create the game database.
    """
    
    # Parse command line arguments
    use_cache = USE_CACHE_BY_DEFAULT
    
    if len(sys.argv) > 1:
        if '--no-cache' in sys.argv:
            use_cache = False
    
    print("Creating Terraforming Mars Game Database")
    print("=" * 50)
    
    # Display analysis settings using shared function
    display_analysis_settings(use_cache=use_cache)
    print("=" * 50)
    
    # Initialize database creator
    creator = GameDatabaseCreator(DATA_DIRECTORY)
    
    # Load all games using existing infrastructure
    games_loaded = creator.load_all_games(use_cache=use_cache)
    
    if games_loaded == 0:
        print("❌ No games found. Please check the data directory path in config.py")
        return
    
    print(f"✅ Loaded {games_loaded} games using existing infrastructure")
    
    # Create the database
    game_database = creator.create_game_database()
    
    # Save the database
    output_file = save_game_database(game_database)
    
    # Save corrections file
    corrections_data = {
        'perspective_corrections': {
            'count': creator._corrected_perspective_count,
            'replay_ids': creator._corrected_perspective_ids,
            'details': creator._perspective_corrections
        },
        'winner_corrections': {
            'count': creator._corrected_winners_count,
            'replay_ids': creator._corrected_winners_ids
        }
    }
    corrections_file = save_corrections_file(corrections_data)
    
    print(f"\n✅ Game database creation complete!")
    print(f"📊 Database contains {len(game_database)} unique games")
    print(f"\nThe database file contains all necessary game metadata:")
    print("- replay_id, player_perspective, winner, generations, prelude_on, game_date, starting_hand")
    print("- Players data: name, corporation, final VP/TR, ELO, ELO change")
    print("- No duplicate data - all player info is stored under the 'players' key")
    print(f"\nCorrections file contains:")
    print("- Player perspective corrections with replay IDs and details")
    print("- Winner corrections with replay IDs")
    print(f"\nYou can now use this database file for game analysis without")
    print(f"reloading all the original game files.")
    print(f"\nUsage tips:")
    print("- Use --no-cache to force reload all files")
    print("- The database respects all filtering settings from config.py")

if __name__ == "__main__":
    main() 