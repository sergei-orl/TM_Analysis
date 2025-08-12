#!/usr/bin/env python3
"""
Script to create a summary JSON from all card analysis files.
Consolidates key information like multiple draws, multiple plays, and move contexts.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

def load_card_analysis(file_path: Path) -> Dict[str, Any]:
    """
    Load a card analysis JSON file.
    
    Args:
        file_path: Path to the card analysis file
        
    Returns:
        Dictionary containing the card analysis data
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {file_path}: {e}")
        return {}

def filter_draw_context(draw_context: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Filter draw_context to only include moves with move_type exactly 'draw' or 'draw_placement'.
    
    Args:
        draw_context: Original draw context dictionary
        
    Returns:
        Filtered draw context dictionary
    """
    filtered_context = {}
    
    for replay_id, moves in draw_context.items():
        filtered_moves = []
        for move in moves:
            move_type = move.get('move_type', '')
            if move_type == 'draw' or move_type == 'draw_placement' or move_type == 'draw_prelude':
                filtered_moves.append(move)
        
        if filtered_moves:  # Only include if there are filtered moves
            filtered_context[replay_id] = filtered_moves
    
    return filtered_context

def create_summary(analysis_dir: str = "analysis_output") -> Dict[str, Any]:
    """
    Create a summary JSON from all card analysis files.
    
    Args:
        analysis_dir: Directory containing card analysis files
        
    Returns:
        Dictionary containing summary information for all cards
    """
    analysis_path = Path(analysis_dir)
    
    if not analysis_path.exists():
        print(f"Analysis directory '{analysis_dir}' not found.")
        return {}
    
    # Find all card analysis files (excluding game_moves files)
    card_files = [f for f in analysis_path.glob("card_analysis_*.json") if "game_moves" not in f.name]
    
    if not card_files:
        print(f"No card analysis files found in '{analysis_dir}'.")
        return {}
    
    print(f"Found {len(card_files)} card analysis files.")
    
    summary = {}
    
    for card_file in card_files:
        print(f"Processing {card_file.name}...")
        
        # Load card analysis
        card_data = load_card_analysis(card_file)
        
        if not card_data:
            continue
        
        card_name = card_data.get('card_name', 'Unknown')
        
        # Extract card name from filename if not in data
        if card_name == 'Unknown':
            card_name = card_file.stem.replace('card_analysis_', '')
        
        # Initialize card summary
        card_summary = {}
        
        # Add multiple draws replay IDs (only if not empty)
        multiple_draws = card_data.get('multiple_draws_games', {})
        if multiple_draws:
            # Filter to only include games where the two draw methods are less than 50 moves apart
            filtered_multiple_draws = {}
            for replay_id, moves in multiple_draws.items():
                # Find draw moves
                draw_moves = [move for move in moves if move.get('move_type', '').startswith('draw')]
                
                if len(draw_moves) >= 2:
                    # Calculate distance between the first two draw moves
                    move_numbers = [move.get('move_number', 0) for move in draw_moves[:2]]
                    distance = abs(move_numbers[1] - move_numbers[0])
                    
                    # Only include if distance < 50
                    if distance < 50:
                        filtered_multiple_draws[replay_id] = moves
            
            if filtered_multiple_draws:
                card_summary['multiple_draws_games'] = filtered_multiple_draws
        
        # Add multiple plays replay IDs (only if not empty)
        multiple_plays = card_data.get('multiple_plays_replay_ids', [])
        if multiple_plays:
            card_summary['multiple_plays_replay_ids'] = multiple_plays
        
        # Add moves where card was seen more than once (only if not empty)
        moves_seen_more_than_once = card_data.get('moves_card_seen_more_than_once', {})
        if moves_seen_more_than_once:
            # Filter to only include seen move types (not draw/play/other)
            filtered_moves = {}
            for replay_id, moves in moves_seen_more_than_once.items():
                # Filter moves to only include seen move types (not starting with draw/play/other)
                seen_moves = []
                for move in moves:
                    move_type = move.get('move_type', '')
                    if not (move_type.startswith('draw') or move_type.startswith('play') or move_type.startswith('other') or move_type.startswith('research_draft_drafted')):
                        seen_moves.append(move)
                
                # Only include if there are seen moves
                if seen_moves:
                    # Check if this case should be filtered out
                    if len(seen_moves) == 2:
                        # Calculate distance between the two moves
                        move_numbers = [move['move_number'] for move in seen_moves]
                        distance = abs(move_numbers[1] - move_numbers[0])
                        
                        # If distance > 50, skip this case
                        if distance > 50:
                            continue
                    
                    # For all other cases, include the full move data
                    filtered_moves[replay_id] = seen_moves
            
            if filtered_moves:
                card_summary['moves_card_seen_more_than_once'] = filtered_moves
        
        # Add played but not drawn IDs (only if not empty)
        played_not_drawn = card_data.get('played_but_not_drawn_ids', [])
        if played_not_drawn:
            card_summary['played_but_not_drawn_ids'] = played_not_drawn
        
        # Try to load context data from separate context file
        context_path = analysis_path / "context" / f"context_{card_name.replace(' ', '_').replace('"', '')}.json"
        if context_path.exists():
            context_data = load_card_analysis(context_path)
            if context_data:
                # Add filtered draw context (only if not empty after filtering)
                draw_context = context_data.get('draw_context', {})
                if draw_context:
                    filtered_draw_context = filter_draw_context(draw_context)
                    if filtered_draw_context:
                        card_summary['draw_context'] = filtered_draw_context
                
                # Add other context (only if not empty)
                other_context = context_data.get('other_context', {})
                if other_context:
                    card_summary['other_context'] = other_context
        
        # Only add card to summary if it has any data
        if card_summary:
            summary[card_name] = card_summary
    
    return summary

def save_summary(summary: Dict[str, Any], output_file: str = "card_analysis_summary.json"):
    """
    Save the summary to a JSON file.
    
    Args:
        summary: Summary dictionary to save
        output_file: Output file path
    """
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        print(f"Summary saved to: {output_file}")
        
        # Show file size
        file_size_mb = Path(output_file).stat().st_size / (1024 * 1024)
        print(f"Summary file size: {file_size_mb:.1f} MB")
        
    except Exception as e:
        print(f"Error saving summary: {e}")

def main():
    """
    Main function to create the summary.
    """
    print("Creating card analysis summary...")
    print("=" * 50)
    
    # Create summary
    summary = create_summary()
    
    if not summary:
        print("No summary data created.")
        return
    
    # Save summary
    save_summary(summary)
    
    # Show summary statistics
    print("\nSummary Statistics:")
    print("=" * 50)
    print(f"Total cards in summary: {len(summary)}")
    
    # List all cards in the summary
    print("\nCards in summary:")
    print("-" * 30)
    card_names = sorted(summary.keys())
    print(",".join(card_names))
    
    # Count cards with each type of data
    cards_with_multiple_draws = sum(1 for card in summary.values() if 'multiple_draws_games' in card)
    cards_with_multiple_plays = sum(1 for card in summary.values() if 'multiple_plays_replay_ids' in card)
    cards_with_moves_seen_more_than_once = sum(1 for card in summary.values() if 'moves_card_seen_more_than_once' in card)
    cards_with_played_not_drawn = sum(1 for card in summary.values() if 'played_but_not_drawn_ids' in card)
    cards_with_draw_context = sum(1 for card in summary.values() if 'draw_context' in card)
    cards_with_other_context = sum(1 for card in summary.values() if 'other_context' in card)
    
    print(f"Cards with multiple draws: {cards_with_multiple_draws}")
    print(f"Cards with multiple plays: {cards_with_multiple_plays}")
    print(f"Cards with moves seen more than once: {cards_with_moves_seen_more_than_once}")
    print(f"Cards played but not drawn: {cards_with_played_not_drawn}")
    print(f"Cards with draw context: {cards_with_draw_context}")
    print(f"Cards with other context: {cards_with_other_context}")
    
    print("\nSummary creation complete!")

if __name__ == "__main__":
    main() 