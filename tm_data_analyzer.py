import json
from pathlib import Path
from typing import Dict
from tqdm import tqdm
import pickle
import hashlib
from card_analyzer import CardAnalyzer
import sys

# Import configuration
try:
    from config import *
except ImportError:
    print("❌ Configuration file 'config.py' not found!")
    print("Please copy 'config_template.py' to 'config.py' and update the paths.")
    sys.exit(1)

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
                    if self._matches_criteria(game_data):
                        game_data['_file_path'] = str(json_file)
                        self.games_data.append(game_data)
                        filtered_games += 1
                    
                    successful_loads += 1
            except Exception as e:
                failed_loads += 1
                print(f"\nError loading {json_file}: {e}")
        
        print(f"\nSuccessfully loaded {successful_loads} files")
        print(f"Found {filtered_games} games matching criteria")
        if failed_loads > 0:
            print(f"Failed to load {failed_loads} files")
        
        # Save to cache for next run (only if no replay filter)
        if use_cache and filtered_games > 0 and not self.replay_id_filter:
            self._save_to_cache()
        
        return len(self.games_data)
    
    def _matches_criteria(self, game_data: Dict) -> bool:
        """
        Check if a game matches the specific criteria.
        
        Args:
            game_data: Game data dictionary
            
        Returns:
            True if game matches criteria, False otherwise
        """
        # Check replay ID filter first (if set)
        if self.replay_id_filter:
            if game_data.get('replay_id') != self.replay_id_filter:
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
            
        return True

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
    print("Starting Terraforming Mars Data Analysis")
    print("=" * 50)
    print(f"Filtering for: {REQUIRED_MAP} map, {REQUIRED_PLAYER_COUNT} players, Colonies={'OFF' if COLONIES_MUST_BE_OFF else 'ON'}, Corporate Era={'ON' if CORPORATE_ERA_MUST_BE_ON else 'OFF'}, Draft={'ON' if DRAFT_MUST_BE_ON else 'OFF'}")
    if replay_id_filter:
        print(f"🔍 Additional filter: Replay ID = {replay_id_filter}")
    print(f"Analyzing card: '{card_name}'")
    print(f"Cache: {'Enabled' if use_cache else 'Disabled'}")
    print("=" * 50)
    
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
