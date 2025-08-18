#!/usr/bin/env python3
"""
Simple script to show which games have multiple perspectives.
Outputs just replay_id and their perspectives.
"""

import json
from pathlib import Path
from collections import defaultdict

def load_game_database(database_path: str = "analysis_output/game_database.json"):
    """Load the game database."""
    try:
        with open(database_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Game database not found at {database_path}")
        print("Please run create_game_database.py first.")
        return None
    except Exception as e:
        print(f"❌ Error loading database: {e}")
        return None

def generate_perspective_summary(game_database):
    """Generate summary of games and their perspectives."""
    perspective_map = defaultdict(list)
    
    # Group games by replay_id
    for game_key, game_data in game_database.items():
        replay_id = game_data.get('replay_id', '')
        player_perspective = game_data.get('player_perspective', '')
        
        if replay_id and player_perspective:
            perspective_map[replay_id].append(player_perspective)
    
    # Generate summary
    summary = {}
    for replay_id, perspectives in perspective_map.items():
        if len(perspectives) > 1:
            # Only include games with multiple perspectives
            summary[replay_id] = perspectives
    
    return summary

def save_perspective_summary(summary, output_path: str = "analysis_output/perspective_summary.json"):
    """Save the perspective summary to a JSON file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    
    print(f"📁 Perspective summary saved to: {output_file}")
    return output_file

def main():
    """Main function."""
    print("Generating Perspective Summary")
    print("=" * 40)
    
    # Load game database
    game_database = load_game_database()
    if not game_database:
        return
    
    print(f"✅ Loaded game database with {len(game_database)} entries")
    
    # Generate summary
    summary = generate_perspective_summary(game_database)
    
    # Display results
    print(f"\n📊 Found {len(summary)} games with multiple perspectives:")
    print("-" * 40)
    
    for replay_id, perspectives in summary.items():
        print(f"{replay_id}: {perspectives}")
    
    # Save to file
    output_file = save_perspective_summary(summary)
    
    print(f"\n✅ Summary complete!")
    print(f"   Total games with multiple perspectives: {len(summary)}")

if __name__ == "__main__":
    main() 