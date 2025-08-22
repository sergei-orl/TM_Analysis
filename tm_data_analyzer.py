import json
from pathlib import Path
from typing import Dict
from tqdm import tqdm
import pickle
import hashlib
from card_analyzer import CardAnalyzer
import sys
import time

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

# Games that should be skipped (hardcoded skips)
SKIPPED_GAMES = [
    "603866588",
    "521063871"
]

class TerraformingMarsAnalyzer:
    """
    Analyzer for Terraforming Mars game data stored in JSON format.
    Focuses on data loading and filtering functionality.
    """
    
    def __init__(self, data_directory: str):
        """
        Initialize the analyzer with the directory containing game data.
        
        Args:
            data_directory: Path to the directory containing game JSON files
        """
        self.data_directory = Path(data_directory)
        self.games_data = []
        self.cache_file = Path("analysis_output/processed_games_cache.pkl")
        self.cache_hash_file = Path("analysis_output/cache_hash.txt")
        self.replay_id_filter = None
        self._processed_games = set()  # Track processed games to avoid duplicates
        
        # Statistics for corrections made during loading
        self._corrections_made = {
            'player_perspective_corrected': 0,
            'winner_corrected': 0,
            'games_skipped_invalid_elo': 0,
            'games_skipped_duplicates': 0,
            'games_skipped_hardcoded': 0
        }
    
    def _get_directory_hash(self) -> str:
        """
        Generate a hash of the data directory to detect changes.
        
        Returns:
            Hash string of the directory
        """
        hash_md5 = hashlib.md5()
        
        # Get all JSON files and their modification times
        json_files = list(self.data_directory.rglob("*.json"))
        file_info = []
        
        for json_file in json_files:
            stat = json_file.stat()
            file_info.append(f"{json_file}:{stat.st_mtime}")
        
        # Sort for consistent hash
        file_info.sort()
        
        # Create hash from file info
        for info in file_info:
            hash_md5.update(info.encode('utf-8'))
        
        return hash_md5.hexdigest()
    
    def _correct_player_perspective(self, moves: list, original_player_perspective: str) -> tuple[str, bool]:
        """
        Detect and correct player perspective based on "You choose corporation" move.
        
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
    
    def _correct_winner(self, game_data: Dict) -> tuple[str, bool]:
        """
        Correct the winner based on ELO data if there's a mismatch.
        
        Args:
            game_data: Game data dictionary
            
        Returns:
            Tuple of (corrected_winner, was_corrected)
        """
        winner = game_data.get('winner', 'unknown')
        players = game_data.get('players', {})
        
        # Find elo_gainer and elo_loser
        elo_gainer = 'unknown'
        elo_loser = 'unknown'
        
        for player_id, player_data in players.items():
            if not isinstance(player_data, dict):
                continue
                
            player_name = player_data.get('player_name', 'unknown')
            elo_data = player_data.get('elo_data')
            
            if elo_data and isinstance(elo_data, dict):
                game_rank_change = elo_data.get('game_rank_change', 0)
                if game_rank_change is not None and isinstance(game_rank_change, (int, float)):
                    if game_rank_change > 0:
                        elo_gainer = player_name
                    elif game_rank_change < 0:
                        elo_loser = player_name
        
        # Correct winner if needed: if elo_gainer != winner and elo_loser == winner, rewrite winner
        if elo_gainer != 'unknown' and elo_gainer != winner and elo_loser == winner:
            return elo_gainer, True
        
        return winner, False
    
    def _has_valid_elo_data(self, game_data: Dict) -> bool:
        """
        Check if a game has valid ELO data for all players.
        
        Args:
            game_data: Game data dictionary
            
        Returns:
            True if all players have valid ELO data, False otherwise
        """
        players = game_data.get('players', {})
        
        for player_data in players.values():
            if not isinstance(player_data, dict):
                return False
                
            elo_data = player_data.get('elo_data')
            if not isinstance(elo_data, dict):
                return False
                
            game_rank_change = elo_data.get('game_rank_change', 0)
            if game_rank_change is None or not isinstance(game_rank_change, (int, float)):
                return False
        
        return True
    
    def _check_and_track_duplicate_game(self, replay_id: str, player_perspective: str) -> bool:
        """
        Check if a game has already been processed and track it if it's a duplicate.
        
        Args:
            replay_id: The replay ID of the game
            player_perspective: The player perspective ID
            
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
    
    def _find_replay_files(self, replay_id: str) -> list:
        """
        Find files containing a specific replay ID in their filename.
        
        Args:
            replay_id: The replay ID to search for
            
        Returns:
            List of Path objects for matching files
        """
        matching_files = []
        
        # Search for files with the replay ID in the filename
        for json_file in self.data_directory.rglob("*.json"):
            if replay_id in json_file.name:
                matching_files.append(json_file)
        
        return matching_files
    
    def _load_from_cache(self) -> bool:
        """
        Try to load processed games from cache.
        
        Returns:
            True if cache was loaded successfully, False otherwise
        """
        if not self.cache_file.exists() or not self.cache_hash_file.exists():
            return False
        
        try:
            # Check if cache is still valid
            with open(self.cache_hash_file, 'r') as f:
                cached_hash = f.read().strip()
            
            current_hash = self._get_directory_hash()
            
            if cached_hash != current_hash:
                print("Cache invalid - data directory has changed")
                return False
            
            # Load cached data
            with open(self.cache_file, 'rb') as f:
                self.games_data = pickle.load(f)
            
            print(f"Loaded {len(self.games_data)} games from cache")
            return True
            
        except Exception as e:
            print(f"Error loading cache: {e}")
            return False
    
    def _save_to_cache(self):
        """
        Save processed games to cache.
        """
        try:
            # Create output directory if it doesn't exist
            self.cache_file.parent.mkdir(exist_ok=True)
            
            # Save processed games
            with open(self.cache_file, 'wb') as f:
                pickle.dump(self.games_data, f)
            
            # Save hash
            with open(self.cache_hash_file, 'w') as f:
                f.write(self._get_directory_hash())
            
            print(f"Saved {len(self.games_data)} games to cache")
            
        except Exception as e:
            print(f"Error saving cache: {e}")
    
    def load_all_games(self, use_cache: bool = True) -> int:
        """
        Load all JSON game files from the data directory and subdirectories.
        Filters for Tharsis map, 2 players, specific settings during loading.
        
        Args:
            use_cache: Whether to use cache for faster loading
            
        Returns:
            Number of games loaded
        """
        print(f"Loading games from: {self.data_directory}")
        
        # Try to load from cache first (only if no replay filter is set)
        if use_cache and not self.replay_id_filter and self._load_from_cache():
            # Apply ALL filters and corrections to cached data (not just additional filters)
            initial_count = len(self.games_data)
            self._apply_all_filters_and_corrections_to_cached_data()
            final_count = len(self.games_data)
            if initial_count != final_count:
                print(f"Applied all filters and corrections: {initial_count} → {final_count} games")
            return len(self.games_data)
        
        # If replay ID filter is set, search for specific file first
        if self.replay_id_filter:
            print(f"🔍 Searching for specific replay ID: {self.replay_id_filter}")
            json_files = self._find_replay_files(self.replay_id_filter)
            if not json_files:
                print(f"❌ No files found for replay ID: {self.replay_id_filter}")
                return 0
            print(f"✅ Found {len(json_files)} file(s) for replay ID: {self.replay_id_filter}")
        else:
            # Find all JSON files recursively
            json_files = list(self.data_directory.rglob("*.json"))
            print(f"Found {len(json_files)} JSON files")
        
        # Add progress bar for loading files
        successful_loads = 0
        failed_loads = 0
        filtered_games = 0
        
        for json_file in tqdm(json_files, desc="Loading and filtering games", unit="file"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    game_data = json.load(f)
                    
                    # Immediate filtering during loading
                    if self._matches_criteria_basic(game_data):
                        game_data['_file_path'] = str(json_file)
                        self.games_data.append(game_data)
                        filtered_games += 1
                    
                    successful_loads += 1
            except Exception as e:
                failed_loads += 1
                print(f"\nError loading {json_file}: {e}")
        
        print(f"\nSuccessfully loaded {successful_loads} files")
        print(f"Found {filtered_games} games matching basic criteria")
        if failed_loads > 0:
            print(f"Failed to load {failed_loads} files")
        
        # Apply Prelude and Starting Hand filters to the loaded data
        if filtered_games > 0:
            initial_count = filtered_games
            self._apply_additional_filters_to_cached_data()
            final_count = len(self.games_data)
            if initial_count != final_count:
                print(f"Applied additional filters: {initial_count} → {final_count} games")
        
        # Save to cache for next run (only if no replay filter)
        if use_cache and filtered_games > 0 and not self.replay_id_filter:
            self._save_to_cache()
        
        # Display correction statistics
        self._display_correction_statistics()
        
        return len(self.games_data)
    
    def _display_correction_statistics(self):
        """
        Display statistics about corrections and filtering made during data loading.
        """
        if any(count > 0 for count in self._corrections_made.values()):
            print("\n📊 Data Loading Corrections and Filtering:")
            if self._corrections_made['player_perspective_corrected'] > 0:
                print(f"  ✅ Player perspective corrected: {self._corrections_made['player_perspective_corrected']} games")
            if self._corrections_made['winner_corrected'] > 0:
                print(f"  ✅ Winner corrected: {self._corrections_made['winner_corrected']} games")
            if self._corrections_made['games_skipped_invalid_elo'] > 0:
                print(f"  ⚠️  Games skipped (invalid ELO): {self._corrections_made['games_skipped_invalid_elo']} games")
            if self._corrections_made['games_skipped_duplicates'] > 0:
                print(f"  ⚠️  Games skipped (duplicates): {self._corrections_made['games_skipped_duplicates']} games")
            if self._corrections_made['games_skipped_hardcoded'] > 0:
                print(f"  ⚠️  Games skipped (hardcoded): {self._corrections_made['games_skipped_hardcoded']} games")
        else:
            print("\n✅ No corrections or filtering needed during data loading")

    def _apply_common_filters(self, game_data: Dict) -> bool:
        """
        Apply common filters that are shared between different filtering methods.
        
        Args:
            game_data: Game data dictionary
            
        Returns:
            True if game passes all common filters, False otherwise
        """
        # Check prelude setting
        if PRELUDE_MUST_BE_ON:
            if not game_data.get('prelude_on', False):
                return False
        
        # Check starting hand requirement
        if MUST_INCLUDE_STARTING_HAND:
            # Check if any player has starting_hand data
            players = game_data.get('players', {})
            has_starting_hand = False
            for player_data in players.values():
                if isinstance(player_data, dict) and 'starting_hand' in player_data:
                    has_starting_hand = True
                    break
            if not has_starting_hand:
                return False
        
        # Check opponent ELO requirement
        if PLAYERS_ELO_OVER_THRESHOLD:
            players = game_data.get('players', {})
            all_players_above_threshold = True

            for player_data in players.values():
                if not isinstance(player_data, dict):
                    all_players_above_threshold = False
                    break

                elo_data = player_data.get('elo_data', {})
                if not isinstance(elo_data, dict):
                    all_players_above_threshold = False
                    break

                game_rank = elo_data.get('game_rank')
                try:
                    if int(game_rank) < ELO_THRESHOLD:
                        all_players_above_threshold = False
                        break
                except (ValueError, TypeError):
                    all_players_above_threshold = False
                    break

            if not all_players_above_threshold:
                return False
        
        # Check conceded filter
        if CONCEDED_OFF and 'conceded' in game_data:
            return False
        
        return True

    def _apply_additional_filters_to_cached_data(self):
        """
        Apply Prelude, Starting Hand, and Opponent ELO filters to already loaded games data.
        This allows changing these filters without rebuilding the cache.
        """
        if not self.games_data:
            return
        
        print(f"Applying additional filters to {len(self.games_data)} cached games...")
        
        # Filter out games that don't match additional criteria
        filtered_games = []
        
        for game_data in tqdm(self.games_data, desc="Filtering cached games", unit="game"):
            # Skip games that are in the SKIPPED_GAMES list
            replay_id = game_data.get('replay_id', '')
            if replay_id in SKIPPED_GAMES:
                self._corrections_made['games_skipped_hardcoded'] += 1
                continue
            
            # Check if game has valid ELO data for all players
            if not self._has_valid_elo_data(game_data):
                self._corrections_made['games_skipped_invalid_elo'] += 1
                continue
            
            # Apply common filters
            if not self._apply_common_filters(game_data):
                continue
            
            # Game passed all additional filters
            filtered_games.append(game_data)
        
        # Update the games data
        self.games_data = filtered_games

    def _apply_all_filters_and_corrections_to_cached_data(self):
        """
        Apply all filters and corrections to already loaded games data.
        This is used when loading from cache to ensure consistency.
        """
        if not self.games_data:
            return
        
        print(f"Applying all filters and corrections to {len(self.games_data)} cached games...")
        
        # Reset corrections tracking since we're applying all logic again
        self._corrections_made = {
            'player_perspective_corrected': 0,
            'winner_corrected': 0,
            'games_skipped_invalid_elo': 0,
            'games_skipped_duplicates': 0,
            'games_skipped_hardcoded': 0
        }
        
        # Reset processed games tracking
        self._processed_games = set()
        
        # Filter out games that don't match additional criteria
        filtered_games = []
        
        for game_data in tqdm(self.games_data, desc="Filtering cached games", unit="game"):
            # Apply common filters
            if not self._apply_common_filters(game_data):
                continue
            
            # Apply player perspective correction if needed
            moves = game_data.get('moves', [])
            if moves:
                original_player_perspective = game_data.get('player_perspective', '')
                if original_player_perspective:
                    corrected_perspective, was_corrected = self._correct_player_perspective(moves, original_player_perspective)
                    if was_corrected:
                        game_data['player_perspective'] = corrected_perspective
                        game_data['_player_perspective_corrected'] = True
                        self._corrections_made['player_perspective_corrected'] += 1
            
            # Apply winner correction if needed
            corrected_winner, winner_was_corrected = self._correct_winner(game_data)
            if winner_was_corrected:
                game_data['winner'] = corrected_winner
                game_data['_winner_corrected'] = True
                self._corrections_made['winner_corrected'] += 1
            
            # Check for duplicate games (same replay_id and player_perspective combination)
            if self._check_and_track_duplicate_game(game_data.get('replay_id', ''), game_data.get('player_perspective', '')):
                self._corrections_made['games_skipped_duplicates'] += 1
                continue
            
            # Game passed all filters and corrections
            filtered_games.append(game_data)
        
        # Update the games data
        self.games_data = filtered_games

    def _matches_criteria_basic(self, game_data: Dict) -> bool:
        """
        Check if a game matches the basic criteria and apply all necessary corrections.
        This is used during initial loading to create the cache.
        
        Args:
            game_data: Game data dictionary
            
        Returns:
            True if game matches basic criteria and passes all filters, False otherwise
        """
        # Check replay ID filter first (if set)
        if self.replay_id_filter:
            if game_data.get('replay_id') != self.replay_id_filter:
                return False
        
        # Skip games that are in the SKIPPED_GAMES list
        replay_id = game_data.get('replay_id', '')
        if replay_id in SKIPPED_GAMES:
            self._corrections_made['games_skipped_hardcoded'] += 1
            return False
        
        # Check map
        if game_data.get('map') != REQUIRED_MAP:
            return False
            
        # Check game settings
        if game_data.get('colonies_on', False) != (not COLONIES_MUST_BE_OFF):
            return False
        if game_data.get('corporate_era_on', False) != CORPORATE_ERA_MUST_BE_ON:
            return False
        if game_data.get('draft_on', False) != DRAFT_MUST_BE_ON:
            return False
        
        # Check number of players
        players = game_data.get('players', {})
        player_count = len([p for p in players.values() if isinstance(p, dict)])
        if player_count != REQUIRED_PLAYER_COUNT:
            return False
        
        # Check if game has valid ELO data for all players
        if not self._has_valid_elo_data(game_data):
            self._corrections_made['games_skipped_invalid_elo'] += 1
            return False
        
        # Apply player perspective correction if needed
        moves = game_data.get('moves', [])
        if moves:
            original_player_perspective = game_data.get('player_perspective', '')
            if original_player_perspective:
                corrected_perspective, was_corrected = self._correct_player_perspective(moves, original_player_perspective)
                if was_corrected:
                    game_data['player_perspective'] = corrected_perspective
                    game_data['_player_perspective_corrected'] = True
                    self._corrections_made['player_perspective_corrected'] += 1
        
        # Apply winner correction if needed
        corrected_winner, winner_was_corrected = self._correct_winner(game_data)
        if winner_was_corrected:
            game_data['winner'] = corrected_winner
            game_data['_winner_corrected'] = True
            self._corrections_made['winner_corrected'] += 1
        
        # Check for duplicate games (same replay_id and player_perspective combination)
        if self._check_and_track_duplicate_game(replay_id, game_data.get('player_perspective', '')):
            self._corrections_made['games_skipped_duplicates'] += 1
            return False
        
        return True

    def analyze_multiple_cards(self, cards_to_analyze: list, use_cache: bool = True):
        """
        Analyze multiple cards using the provided analyzer.
        This function can be reused by other scripts to avoid duplication.
        
        Args:
            analyzer: Initialized TerraformingMarsAnalyzer instance
            cards_to_analyze: List of card names to analyze
            use_cache: Whether cache is enabled
            
        Returns:
            Tuple of (successful_analyses, failed_analyses)
        """
        # Load all games (filtering happens during loading)
        print("\nLoading games data...")
        games_loaded = self.load_all_games(use_cache=use_cache)
        
        if games_loaded == 0:
            print("No games found matching criteria. Please check the data directory path in config.py")
            return 0, 0
        
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
                card_analyzer = CardAnalyzer(self.games_data)
                
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
        
        return successful_analyses, failed_analyses

def display_analysis_settings(replay_id_filter: str = None, card_name: str = None, use_cache: bool = True):
    """
    Display the current analysis settings in a formatted way.
    This function can be reused by other scripts to avoid duplication.
    
    Args:
        replay_id_filter: Optional replay ID filter to display
        card_name: Optional card name to display
        use_cache: Whether cache is enabled
    """
    print("Starting Terraforming Mars Data Analysis")
    print("=" * 50)
    print(f"Filtering for: {REQUIRED_MAP} map, {REQUIRED_PLAYER_COUNT} players")
    print(f"Colonies: {'OFF' if COLONIES_MUST_BE_OFF else 'ON'}")
    print(f"Corporate Era: {'ON' if CORPORATE_ERA_MUST_BE_ON else 'OFF'}")
    print(f"Draft: {'ON' if DRAFT_MUST_BE_ON else 'OFF'}")
    
    print(f"Prelude Required: {'Yes' if PRELUDE_MUST_BE_ON else 'No'}")
    print(f"Starting Hand Required: {'Yes' if MUST_INCLUDE_STARTING_HAND else 'No'}")
    print(f"Players ELO Over Threshold Required: {'Yes' if PLAYERS_ELO_OVER_THRESHOLD else 'No'}")
    print(f"Skip Conceded Games: {'Yes' if CONCEDED_OFF else 'No'}")
    
    if replay_id_filter:
        print(f"🔍 Additional filter: Replay ID = {replay_id_filter}")
    if card_name:
        print(f"Analyzing card: '{card_name}'")
    print(f"Cache: {'Enabled' if use_cache else 'Disabled'}")
    print("=" * 50)

def main():
    """
    Main function to run the Terraforming Mars analyzer.
    Focuses on card analysis for specific cards.
    """
    
    # Parse command line arguments
    use_cache = USE_CACHE_BY_DEFAULT
    card_name = DEFAULT_CARD
    replay_id_filter = None
    
    if len(sys.argv) > 1:
        if '--no-cache' in sys.argv:
            use_cache = False
        if '--card' in sys.argv:
            card_index = sys.argv.index('--card')
            if len(sys.argv) > card_index + 1:
                card_name = sys.argv[card_index + 1]
        if '--replay' in sys.argv:
            replay_index = sys.argv.index('--replay')
            if len(sys.argv) > replay_index + 1:
                replay_id_filter = sys.argv[replay_index + 1]
    
    # Initialize analyzer with path from config
    analyzer = TerraformingMarsAnalyzer(DATA_DIRECTORY)
    
    # Set replay ID filter if specified
    if replay_id_filter:
        analyzer.replay_id_filter = replay_id_filter
        print(f"🔍 Filtering for specific replay ID: {replay_id_filter}")
    
    # Load all games (filtering happens during loading)
    display_analysis_settings(replay_id_filter, card_name, use_cache)
    
    games_loaded = analyzer.load_all_games(use_cache=use_cache)
    
    if games_loaded == 0:
        print("No games found matching criteria. Please check the data directory path in config.py")
        return
    
    print(f"\nLoaded {games_loaded} filtered games...")
    
    # Analyze specific card
    print(f"\nAnalyzing card: '{card_name}'")
    card_analyzer = CardAnalyzer(analyzer.games_data)
    card_stats = card_analyzer.save_card_analysis(card_name)
    
    if card_stats['total_games_analyzed'] > 0:
        print(f"\n✅ Analyzed {card_stats['total_games_analyzed']} games for '{card_name}'!")
        print(f"📁 Results saved to: analysis_output/card_analysis_{card_name.replace(' ', '_').replace('"', '')}.json")
    else:
        print(f"\n❌ No games found for card: '{card_name}'")
    
    print("\nAnalysis complete!")
    print("\nUsage tips:")
    print("- Use --no-cache to force reload all files")
    print("- Use --card 'Card Name' to analyze different card")
    print("- Use --replay 123456789 to analyze only one specific game")
    print("- Example: python tm_data_analyzer.py --card 'Standard Technology'")
    print("- Example: python tm_data_analyzer.py --replay 123456789 --card 'Moss'")
    print("\nConfiguration:")
    print("- Update config.py to change data directory and other settings")


if __name__ == "__main__":
    main()
