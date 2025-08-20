import json
from collections import Counter
from pathlib import Path
from typing import Dict, Any
from tqdm import tqdm
import re
from config import MUST_INCLUDE_STARTING_HAND

FREE_DRAW_METHODS = [
    "draw", "draw_ai_central", "draw_convoy_from_europa", "draw_development_center",
    "draw_lagrange_observatory", "draw_large_convoy", "draw_mars_university", 
    "draw_martian_survey", "draw_olympus_conference", "draw_placement", 
    "draw_placement_23_Ascraeus", "draw_placement_58", "draw_placement_61", 
    "draw_placement_68", "draw_placement_82", "draw_point_luna", "draw_research", 
    "draw_sf_memorial", "draw_technology_demonstration", "draw_inventrix",
    "draw_prelude_biolabs", "draw_prelude_io_research_outpost",
    "draw_prelude_research_network", "draw_prelude_unmi_contractor",
    "draw_reveal_plant_tag", "draw_reveal_space_tag"
]

BUY_METHODS = [
    "draw_business_network_buy", "draw_inventors_guild_buy", "draw_draft_buy"
]

CARD_CONFUSION_PATTERNS = {
    "Algae": ["Arctic Algae"],
    "Moss": ["Nitrophilic Moss"],
    "Mine": ["Strip Mine", "Titanium Mine"],
    "Comet": ["Towing a Comet"],
    "Lichen": ["Adapted Lichen"],
    "Asteroid": ["Asteroid Mining", "Ammonia Asteroid", "Big Asteroid", "Thorium Asteroid","Ice Asteroid", 
                    "pays 14 (Asteroid)", "Rich Asteroid", "standard project Asteroid", "Huge Asteroid"],
    "Asteroid Mining": ["Asteroid Mining Consortium"],
    "Ice Asteroid": ["Giant Ice Asteroid"],
    "Farming": ["Kelp Farming", "Noctis Farming", "Tundra Farming", "Dome Farming"],
    "Research": ["Research Coordination", "Research Outpost", "Research draft", "Research Network"],
    "Research Outpost": ["Io Research Outpost"],
    "Shuttles": ["Immigration Shuttles"]
}
        

class CardAnalyzer:
    """
    Dedicated analyzer for card-specific analysis functionality.
    """
    
    def __init__(self, games_data: list):
        """
        Initialize the card analyzer with processed games data.
        
        Args:
            games_data: List of processed game data dictionaries
        """
        self.games_data = games_data
    
    def _initialize_card_stats(self, card_name: str) -> Dict[str, Any]:
        """
        Initialize the card statistics dictionary.
        
        Args:
            card_name: Name of the card to analyze
            
        Returns:
            Dictionary with initialized card statistics
        """
        return {
            'card_name': card_name,
            'total_games_analyzed': 0,
            'total_games_with_card': 0,  # Games where card appeared in any way
            'kept_in_starting_hand': 0,
            'drawn_by_generation': Counter(),
            'played_by_generation': Counter(),
            'seen_count': 0,
            'drawn_count': 0,
            'played_count': 0,
            'kept_and_played': 0,
            'kept_but_not_played': 0,
            'payment_amounts': [],  # List of payment amount lists for each play
            'draw_methods': Counter(),  # Track frequency of each draw method
            'seen_methods': Counter(),  # Track frequency of each seen method
            'other_stats': Counter(),  # Track frequency of other types
            'draw_free': Counter(),  # Track free draws by generation
            'draw_and_buy': Counter(),  # Track draws that involve buying by generation
            'draw_for_2': Counter(),  # Track draws from Restricted Area by generation
            'drawn_and_played_by_gen': [],  # List of (drawn_gen, played_gen) tuples
            'drawn_not_played_by_gen': [],  # List of drawn_gen for cards that were drawn but not played
            'moves_card_seen_more_than_once': {},  # Only games with multiple seen_method moves
            'multiple_draws_games': {},  # Special tracking for games with multiple draws
            'played_but_not_drawn_ids': [],  # Track replay IDs of games where cards were played but not drawn
            'draft_takeback_context': {}, # Track context for draft moves with takebacks
            'draft_no_takebacks_context': {}, # Track context for draft moves without takebacks
            'draw_context': {},  # Track context for "draw" moves
            'draw_draft_buy_context': {},  # Track context for draw_draft_buy moves
            'other_context': {},  # Track context for "other" moves
            'game_moves_by_card': {},  # Store all moves that contain the card name
            'draw_draft_buy_without_draft_ids': [],  # Track replay IDs where draw_draft_buy occurs without corresponding draft moves
            # Player performance analysis
            'win_count': 0,  # Number of games won by player_perspective
            'elo_gains': {
                '-19 and down': 0,
                '-17 to -18': 0,
                '-15 to -16': 0,
                '-13 to -14': 0,
                '-11 to -12': 0,
                '-9 to -10': 0,
                '-7 to -8': 0,
                '-5 to -6': 0,
                '-3 to -4': 0,
                '-1 to -2': 0,
                '0': 0,
                '1 to 2': 0,
                '3 to 4': 0,
                '5 to 6': 0,
                '7 to 8': 0,
                '9 to 10': 0,
                '11 to 12': 0,
                '13 to 14': 0,
                '15 to 16': 0,
                '17 to 18': 0,
                '19 and up': 0
            },  # Distribution of ELO gains in buckets
            'actual_elo_values': [],  # Store actual ELO values for accurate average calculation
            'game_ranks': [],  # Store actual ELO ratings at game start for average calculation
            'player_corporations': Counter(),  # Track corporations used by player_perspective
            # New fields for different win percentage calculations
            'total_games_when_seen': 0,  # Games where card was seen (excluding reveal moves)
            'total_games_when_with_card_in_hand': 0,  # Games where card was drawn
            'total_games_when_bought_during_game': 0,  # Games where card was bought during game
            'total_games_when_played': 0,  # Games where card was played
            'win_count_when_seen': 0,  # Wins when card was seen
            'win_count_when_drawn': 0,  # Wins when card was drawn
            'win_count_when_bought_during_game': 0,  # Wins when card was bought during game
            'win_count_when_played': 0,  # Wins when card was played
            'keep_rates': {},
            # Prelude tracking
            'games_with_prelude': 0,  # Games where prelude_on = True
            'games_without_prelude': 0,  # Games where prelude_on = False
            'wins_with_prelude': 0,  # Wins when prelude_on = True
            'wins_without_prelude': 0,  # Wins when prelude_on = False
            'win_rate_with_prelude': 0,  # Win percentage when prelude_on = True
            'win_rate_without_prelude': 0,  # Win percentage when prelude_on = False
            # New buy rate tracking
            'card_buy_through_card_rate': 0,  # Rate of buys through Business Network/Inventors' Guild
            'buy_to_draft_rate': 0,  # Rate of buys vs drafts overall
            'buy_to_draft_1_rate': 0,  # Rate of buys vs draft_1 specifically
            'buy_to_draft_2_rate': 0,  # Rate of buys vs draft_2 specifically
            'buy_to_draft_3_rate': 0,  # Rate of buys vs draft_3 specifically
            'buy_to_draft_4_rate': 0,  # Rate of buys vs draft_4 specifically
            # Track buys for each draft number separately
            'draft_1_buys': 0,  # Buys that occurred after draft_1
            'draft_2_buys': 0,  # Buys that occurred after draft_2
            'draft_3_buys': 0,  # Buys that occurred after draft_3
            'draft_4_buys': 0,  # Buys that occurred after draft_4
            # New play rate tracking
            'play_to_buy_during_game_rate': 0,  # Play rate when card was bought during game
            'play_to_buy_overall_rate': 0,  # Play rate when card was bought (during game + starting hand)
            'play_to_draw_for_free_rate': 0,  # Play rate when card was drawn (excluding buy methods and starting hand)
            'play_per_option_rate': 0,  # Play rate when card was seen (option to pick)
            'play_per_card_in_hand_rate': 0,  # Play rate when card was drawn (in hand)
            # Track plays under each condition separately
            'plays_when_bought_during_game': 0,  # Plays in games where card was bought during game
            'plays_when_bought_overall': 0,  # Plays in games where card was bought (during game + starting hand)
            'plays_when_drawn_for_free': 0,  # Plays in games where card was drawn (excluding buy methods and starting hand)
            # Separate ELO tracking for each case - allows us to calculate average ELO gains and ratings
            # for different scenarios (when card was seen, drawn, bought, played, and by prelude status)
            'elo_values_when_seen': [],  # ELO values when card was seen
            'elo_values_when_drawn': [],  # ELO values when card was drawn
            'elo_values_when_bought_during_game': [],  # ELO values when card was bought during game
            'elo_values_when_played': [],  # ELO values when card was played
            'game_ranks_when_seen': [],  # ELO ratings at game start when card was seen
            'game_ranks_when_drawn': [],  # ELO ratings at game start when card was drawn
            'game_ranks_when_bought_during_game': [],  # ELO ratings at game start when card was bought during game
            'game_ranks_when_played': [],  # ELO ratings at game start when card was played
        }
    
    def _get_elo_bucket(self, elo_value: int) -> str:
        """
        Get the appropriate ELO bucket for a given ELO value.
        
        Args:
            elo_value: ELO gain/loss value
            
        Returns:
            String representing the ELO bucket
        """
        if elo_value <= -19:
            return '-19 and down'
        elif elo_value <= -17:
            return '-17 to -18'
        elif elo_value <= -15:
            return '-15 to -16'
        elif elo_value <= -13:
            return '-13 to -14'
        elif elo_value <= -11:
            return '-11 to -12'
        elif elo_value <= -9:
            return '-9 to -10'
        elif elo_value <= -7:
            return '-7 to -8'
        elif elo_value <= -5:
            return '-5 to -6'
        elif elo_value <= -3:
            return '-3 to -4'
        elif elo_value <= -1:
            return '-1 to -2'
        elif elo_value == 0:
            return '0'
        elif elo_value <= 2:
            return '1 to 2'
        elif elo_value <= 4:
            return '3 to 4'
        elif elo_value <= 6:
            return '5 to 6'
        elif elo_value <= 8:
            return '7 to 8'
        elif elo_value <= 10:
            return '9 to 10'
        elif elo_value <= 12:
            return '11 to 12'
        elif elo_value <= 14:
            return '13 to 14'
        elif elo_value <= 16:
            return '15 to 16'
        elif elo_value <= 18:
            return '17 to 18'
        else:
            return '19 and up'

    def _check_pattern_in_descriptions(self, pattern: str, descriptions: list, action_types: list = None, is_regex: bool = False, action_type: str = None) -> bool:
        """
        Check if a pattern appears in any of the provided descriptions.
        
        Args:
            pattern: Pattern to search for (string or regex)
            descriptions: List of descriptions to check
            action_types: Optional list of action types to match (same length as descriptions)
            is_regex: Whether pattern is a regex pattern (default: False)
            action_type: Action type to match (optional)
            
        Returns:
            True if pattern is found in any description (and action_type matches if provided)
        """
        for i, desc in enumerate(descriptions):
            if desc:
                if is_regex:
                    if re.search(pattern, desc):
                        if action_types is None or (i < len(action_types) and action_types[i] == action_type):
                            return True
                else:
                    if pattern in desc:
                        if action_types is None or (i < len(action_types) and action_types[i] == action_type):
                            return True
        return False
    
    def _check_kept_in_starting_hand(self, moves: list, player_perspective: str, card_name: str) -> bool:
        """
        Check if card was kept in starting hand.
        
        Args:
            moves: List of moves for the game
            player_perspective: Player ID to focus on
            card_name: Name of the card to check
            
        Returns:
            True if card was kept in starting hand, False otherwise
        """
        kept_in_hand = False
        for move in moves:
            if not isinstance(move, dict):
                continue
                
            # Only consider moves from player_perspective
            if move.get('player_id') != player_perspective:
                continue
            
            description = move.get('description', '')
            
            # Look for "You choose" followed by card name
            if "You choose" in description:
                # Check for specific patterns to avoid wrong attributions
                # Pattern 1: "You buy {card_name} |"
                # Pattern 2: "You buy {card_name}" at end of string
                buy_pattern_1 = f"You buy {card_name} |"
                buy_pattern_2 = f"You buy {card_name}"
                
                if (buy_pattern_1 in description or 
                    description.endswith(buy_pattern_2)):
                    kept_in_hand = True
                else:
                    kept_in_hand = False

            
            # If we find "plays" before finding "You choose", card was not kept
            if "plays" in description:
                break
        
        return kept_in_hand    
    
    def _strip_confusing_patterns(self, description: str, card_name: str) -> str:
        """
        Strip confusing card patterns from a description to avoid false positives.
        
        Args:
            description: Description to clean
            card_name: Name of the card being analyzed
            
        Returns:
            Cleaned description with confusing patterns removed
        """
        if not description or card_name not in CARD_CONFUSION_PATTERNS:
            return description
            
        cleaned_description = description
        conflicting_cards = CARD_CONFUSION_PATTERNS[card_name]
        
        # Remove all conflicting card names from the description
        for conflicting_card in conflicting_cards:
            cleaned_description = cleaned_description.replace(conflicting_card, "")
        
        # Special handling for Mine card - also exclude any "Mine" followed by a letter
        if card_name == "Mine":
            cleaned_description = re.sub(r'Mine[a-z]', '', cleaned_description)
            
        return cleaned_description

    def _check_wrong_card_attribution(self, card_name: str, current_description: str, player_perspective_name: str, opponent_name: str) -> bool:
        """
        Check if a move represents wrong card attribution (e.g., "Algae" vs "Arctic Algae").
        Also checks for player names that might contain the card name.
        
        Args:
            card_name: Name of the card to check
            current_description: Current move description
            player_perspective_name: Name of the player perspective
            opponent_name: Name of the opponent player
            
        Returns:
            True if this move should be skipped due to wrong attribution
        """

        # Start with the original description and apply card confusion patterns
        description_to_check = self._strip_confusing_patterns(current_description, card_name)
        
        # Apply player name filtering
        for player_name in [player_perspective_name, opponent_name]:
            if player_name and card_name in player_name:
                # Player name contains the card name, exclude it entirely from the description
                if player_name in description_to_check:
                    # Remove the player name from the description to avoid false positives
                    description_to_check = description_to_check.replace(player_name, "")
        
        # Final check: does the standalone card name exist after removing all conflicts?
        if card_name not in description_to_check:
            return True
        
        return False

    def _detect_draw_move(self, card_name: str, descriptions: list, action_types: list,
                          next_description: str, next_2_description: str, next_player_id: str = None,
                          player_perspective: str = None, player_perspective_name: str = None, 
                          opponent_name: str = None, generation: int = None) -> str:
        """
        Detect if a move represents a draw and determine the draw type.
        
        Args:
            card_name: Name of the card to check
            descriptions: List of descriptions to check
            action_types: List of action types to check
            next_description: Next move description
            next_player_id: Player ID of the next move
            player_perspective: Player ID to focus on
            player_perspective_name: Name of the player perspective
            opponent_name: Name of the opponent player
            generation: Generation number
            
        Returns:
            The move type string
        """
        current_description = descriptions[0]
        current_action_type = action_types[0]
        prev_description = descriptions[1]
        
        # Only check for specific cases to avoid unnecessary regex for other cards
        if player_perspective_name and opponent_name and self._check_wrong_card_attribution(card_name, current_description, player_perspective_name, opponent_name):
            return "skip_wrong_attribution"
        
        if re.search(fr"plays card {card_name}", prev_description) or re.search(fr"plays card {card_name}", current_description):
            if not (
                card_name == "Research" and re.search(r"plays card Research (Network|Coordination|Outpost)", prev_description)
            ):
                return "other"

        if re.search(fr"places (tile )?{card_name}", current_description):
            return "other"

        if re.search(fr"places (City on {card_name}|tile City into {card_name})", current_description):
            return "other"

        if card_name == "Lava Flows":
            if current_action_type == "place_tile" and re.search(r"places Ocean.*\(Lava Flows\)", current_description):
                return "other"
            if re.search(r"gains [12].*\(Lava Flows\)", current_description):
                return "other"

        if card_name in ("Capital", "Ecological Zone", "Restricted Area"):
            if re.search(fr"gains [12].*\({card_name}\)", current_description):
                return "other"

        
        if f"places tile City into {card_name}" in current_description:
            return "other"
        
        if f"activates {card_name}" in current_description:
            return "other"
        
        if f"triggered effect of {card_name}" in current_description:
            return "other"
        
        if f"activation effect of {card_name}" in current_description:
            return "other"
        
        if f"immediate effect of {card_name}" in current_description:
            return "other"
        
        if f"scores" in current_description and f"for card {card_name}" in current_description:
            return "other"
        
        if f"scores" in current_description and f"for city tile at {card_name}" in current_description:
            return "other"
        
        if f"adds Science to {card_name}" in current_description or f"removes Science from {card_name}" in current_description:
            return "other"
        
        if f"copies production box of {card_name}" in current_description:
            return "other"
        
        if f"adds Microbe to {card_name}" in current_description or f"removes Microbe from {card_name}" in current_description:
            return "other"
        
        if f"adds Animal to {card_name}" in current_description or f"removes Animal from {card_name}" in current_description:
            return "other"
        
        if f"moves Resource into {card_name}" in current_description:
            return "other"
        
        if f"reveals {card_name}: it has a Space tag" in current_description:
            return "draw_reveal_space_tag"
        
        if f"reveals {card_name}: it has a Plant tag" in current_description:
            return "draw_reveal_plant_tag"
        
        # Draft cards
        if current_action_type == "draft_card":
            if f"{player_perspective_name} takes back their move" in next_description:
                if next_player_id == player_perspective or not next_player_id:
                    return "other"
                else:
                    return "draft"
            elif f"You draft {card_name}" in next_description:
                return "other"
            else:
                return "draft"
        
        # Research draft
        if "Research draft" in current_description:
            return "research_draft"
        
        # Starting hand selection
        if "You choose corporation" in current_description and f"You buy {card_name}" in current_description:
            # Check that the next move is from the same player (player_perspective)
            if f"{player_perspective_name} takes back their move" in next_description:
                if next_player_id == player_perspective or not next_player_id:
                    return "other"
                else:
                    return "draw_start"
            elif f"You choose corporation" in next_description:
                return "other"
            else:
                return "draw_start"
        
        # Reveals (card shown but not drawn)
        if f"reveals {card_name}:" in current_description or f"reveals {card_name} |" in current_description:
            if "it does not have a Microbe tag" in current_description or "it has a Microbe tag" in current_description:
                return "reveal_microbe"
            elif "it does not have a Plant tag" in current_description:
                return "reveal_plant"
            elif "it does not have a Space tag" in current_description:
                return "reveal_space"
            else:
                return "reveal"
        
        if ("draws 3 cards" in current_description and self._check_pattern_in_descriptions("plays card Research Network", descriptions) and
            not ("You keep" in next_description)):
            return "draw_prelude_research_network"
        
        if ("draws 3 cards" in current_description and self._check_pattern_in_descriptions("plays card Biolabs", descriptions) and
            not ("You keep" in next_description)):
            return "draw_prelude_biolabs"
        
        # Prelude draws (draws 3 cards with play_card action)
        if "draws 3 cards" in current_description and current_action_type == "play_card":
            return "draw_prelude"
        
        if ("draws 3 cards" in current_description and 
            (self._check_pattern_in_descriptions("mandatory action to perform", descriptions) or
            self._check_pattern_in_descriptions("corporation Inventrix", descriptions))):
            return "draw_inventrix"
        
        # Invention contest draws (draws 3 cards without play_card)
        if "draws 3 cards" in current_description and current_action_type != "play_card":
            if self._check_pattern_in_descriptions("You keep", [next_description, next_2_description]):
                return "invention_contest_draw"
            elif generation == 1:
                return "draw_inventrix"
            else:
                print(f"WARNING: Unidentified description for 'draws 3 cards': {current_description}")
                pass
        
        # Business contacts draws (draws 4 cards without Research draft)
        if "draws 4 cards" in current_description and "Research draft" not in current_description:
            return "business_contacts_draw"
        
        # Card-specific draws based on previous moves
        # Non-draw types (don't count in stats)
        if self._check_pattern_in_descriptions("activates Business Network", descriptions, action_types, action_type="activate_card"):
            if f"You buy {card_name}" in current_description:
                return "draw_business_network_buy"
            elif "draws 1 card" in current_description and not self._check_pattern_in_descriptions("activates Restricted Area", [current_description]):
                return "business_network_draw"
        if self._check_pattern_in_descriptions("activates Inventors' Guild", descriptions, action_types, action_type="activate_card"):
            if f"You buy {card_name}" in current_description:
                return "draw_inventors_guild_buy"
            elif "draws 1 card" in current_description and not self._check_pattern_in_descriptions("activates Restricted Area", [current_description]):
                return "inventors_guild_draw"
        
        # Draw types (count in stats)
        if self._check_pattern_in_descriptions("plays card UNMI Contractor", descriptions[:3], action_types[:3], action_type="play_card"):
            return "draw_prelude_unmi_contractor"
        if self._check_pattern_in_descriptions("plays card Io Research Outpost", descriptions[:3], action_types[:3], action_type="play_card"):
            return "draw_prelude_io_research_outpost"
        if ((self._check_pattern_in_descriptions("activates AI Central", descriptions, action_types, action_type="activate_card") or
            self._check_pattern_in_descriptions("activates AI Central", descriptions, action_types, action_type="pass")) and
            "draws 2 cards" in current_description):
            return "draw_ai_central"
        if ((self._check_pattern_in_descriptions("activates Restricted Area", descriptions, action_types, action_type="activate_card") or
            self._check_pattern_in_descriptions("activates Restricted Area", descriptions, action_types, action_type="pass")) and
            not ("draws 2 cards" in current_description) and
            not ("activates Development Center" in current_description)):
            return "draw_restricted_area"
        if ((self._check_pattern_in_descriptions("activates Development Center", descriptions, action_types, action_type="activate_card") or
            self._check_pattern_in_descriptions("activates Development Center", descriptions, action_types, action_type="pass")) and
            not ("draws 2 cards" in current_description)):
            return "draw_development_center"
        if self._check_pattern_in_descriptions("plays card SF Memorial", descriptions):
            return "draw_sf_memorial"
        if self._check_pattern_in_descriptions("plays card Convoy From Europa", descriptions):
            return "draw_convoy_from_europa"
        if (self._check_pattern_in_descriptions("plays card Large Convoy", descriptions) and
            "draws 2 cards" in current_description):
            return "draw_large_convoy"
        if (self._check_pattern_in_descriptions("plays card Research", descriptions) and "draws 2 cards" in current_description):
            if card_name == "Research":
                return "other"
            else:
                return "draw_research"
        if self._check_pattern_in_descriptions("plays card Lagrange Observatory", descriptions):
            return "draw_lagrange_observatory"
        if self._check_pattern_in_descriptions("plays card Martian Survey", descriptions):
            return "draw_martian_survey"
        if self._check_pattern_in_descriptions("plays card Technology Demonstration", descriptions):
            return "draw_technology_demonstration"
        if (self._check_pattern_in_descriptions("removes Science from Olympus Conference", descriptions) and
             not ("draws 2 cards" in current_description) and not ("You keep" in current_description)):
            return "draw_olympus_conference"

        # Placement draws - check for tile coordinates in brackets
        if self._check_pattern_in_descriptions(r'\(6,1\)', descriptions, is_regex=True):
            return "draw_placement_61"
        if self._check_pattern_in_descriptions(r'\(8,2\)', descriptions, is_regex=True):
            return "draw_placement_82"
        if self._check_pattern_in_descriptions(r'\(5,8\)', descriptions, is_regex=True):
            return "draw_placement_58"
        if self._check_pattern_in_descriptions(r'\(6,8\)', descriptions, is_regex=True):
            return "draw_placement_68"
        if (self._check_pattern_in_descriptions(r'\(2,3\)', descriptions, is_regex=True) or
            self._check_pattern_in_descriptions("Ascraeus Mons", descriptions)):
            return "draw_placement_23_Ascraeus"
        
        # Invention Contest keep
        if ("You keep" in current_description and 
            not self._check_pattern_in_descriptions("You keep Invention Contest", descriptions) and
            self._check_pattern_in_descriptions("Invention Contest", descriptions)):
            return "draw_invention_contest_keep"
        
        # Business Contacts keep
        if ("You keep" in current_description and
            not self._check_pattern_in_descriptions("draws 3 cards", descriptions) and
            not self._check_pattern_in_descriptions("You buy Business Contacts", [current_description]) and
            (self._check_pattern_in_descriptions("Business Contacts", descriptions) or
            self._check_pattern_in_descriptions("draws 4 cards", descriptions))):
            return "draw_business_contacts_keep"
        
        if self._check_pattern_in_descriptions("triggered effect of Point Luna", descriptions):
            # Check if the same player played this card in the same context
            card_played_by_player = False
            for desc in descriptions:
                if desc and f"plays card {card_name}" in desc:
                    card_played_by_player = True
                    break
            
            if not card_played_by_player:
                return "draw_point_luna"
            else:
                return "other"
        
        # Mars University
        if (
            (self._check_pattern_in_descriptions("triggered effect of Mars University", descriptions) or
            self._check_pattern_in_descriptions("discards", descriptions)) and
            not ("draws 2 cards" in current_description)
        ):
            return "draw_mars_university"
        
        # Placement draws by action_type
        if ("place_tile" in action_types):
            if "draws 2 cards" in current_description:
                return "draw_placement_82"
            else:
                return "draw_placement"
        
        # Buy card during draft
        if f"You buy {card_name}" in current_description:
            pays_and_keeps = (
                f"pays" in current_description and
                f"keeps" in current_description
            )
            pays_fixed_amount = (
                f"pays 6" in current_description or
                f"pays 9" in current_description or
                f"pays 12" in current_description
            )

            if pays_and_keeps or pays_fixed_amount or "draft_card" in action_types:
                if f"You buy {card_name}" in next_2_description:
                    return "other"
                elif f"{player_perspective_name} takes back their move" in next_description:
                    if next_player_id == player_perspective or not next_player_id:
                        return "other"
                    else:
                        return "draw_draft_buy"
                else:
                    return "draw_draft_buy"
        
        # Regular draws (buy, draw, keep)
        if ("buy" in current_description or "draw" in current_description or "keep" in current_description):
            if "draws 10 cards" in current_description or f"{player_perspective_name} takes back their move" in next_description:
                return "other"
            elif "buy" in current_description:
                return "draw_draft_buy"
            else:
                return "draw"
        
        return "other"
    
    def _determine_draft_type(self, moves: list, current_move_index: int, player_perspective: str, card_name: str, player_perspective_name: str, opponent_name: str) -> dict:
        """
        Determine the draft type (draft_1, draft_2, draft_3, or draft_4) and track takeback information.
        
        Args:
            moves: List of all moves for the game
            current_move_index: Index of the current draft move
            player_perspective: Player ID to focus on
            card_name: Name of the card being analyzed
            player_perspective_name: Name of the player perspective
            opponent_name: Name of the opponent player
            
        Returns:
            Dictionary with draft_type, has_takeback flag, and incorrect_draft if applicable
        """
        # Find the first previous move with action_type "pass"
        pass_move_index = None
        for i in range(current_move_index - 1, -1, -1):
            if moves[i].get('action_type') == 'pass' or "pass" in moves[i].get('description', ''):
                pass_move_index = i
                break
        
        # If no pass move found, this is strange
        if pass_move_index is None:
            return {"draft_type": "draft_unknown", "has_takeback": False}
        
        # Check if pass move contains the card name
        pass_move = moves[pass_move_index]
        pass_description = pass_move.get('description', '')
        pass_contains_card = not self._check_wrong_card_attribution(card_name, pass_description, player_perspective_name, opponent_name)
        
        # Analyze moves between pass and current draft
        draft_card_count = 0
        takeback_count = 0
        
        for i in range(pass_move_index + 1, current_move_index):
            move = moves[i]
            action_type = move.get('action_type', '')
            player_id = move.get('player_id', '')
            description = move.get('description', '')
            
            # Count draft_card moves
            if action_type == 'draft_card':
                draft_card_count += 1
            
            # Count takeback moves for the player_perspective
            if (player_id == player_perspective and 
                "takes back" in description):
                takeback_count += 1
        
        # Calculate final draft number
        # Subtract takeback count from draft_card count
        final_draft_number = 1 + draft_card_count - takeback_count
        
        # Ensure the result is at least 1
        if final_draft_number < 1:
            final_draft_number = 1
        
        # Cap at 4
        if final_draft_number > 4:
            final_draft_number = 4
        
        # Apply card name validation rules
        incorrect_draft = None
        corrected_draft_type = f"draft_{final_draft_number}"
                
        if pass_contains_card:
            # Pass contains card_name: only draft_1 or draft_3 are valid
            if final_draft_number == 2:
                corrected_draft_type = "draft_1"
                incorrect_draft = 2
            elif final_draft_number == 4:
                corrected_draft_type = "draft_3"
                incorrect_draft = 4
        else:
            # Pass doesn't contain card_name: only draft_2 or draft_4 are valid
            if final_draft_number == 1:
                corrected_draft_type = "draft_2"
                incorrect_draft = 1
            elif final_draft_number == 3:
                # Check if current move contains "draft" more than once
                current_move = moves[current_move_index]
                current_description = current_move.get('description', '')
                draft_word_count = current_description.lower().count('draft')
                
                if draft_word_count > 1:
                    corrected_draft_type = "draft_4"
                else:
                    corrected_draft_type = "draft_2"
                incorrect_draft = 3
                
        result = {
            "draft_type": corrected_draft_type,
            "has_takeback": takeback_count > 0
        }
        
        if incorrect_draft is not None:
            result["incorrect_draft"] = incorrect_draft
        
        return result

    def _track_move_context(self, card_stats: Dict[str, Any], replay_id: str, 
                           moves: list, current_index: int, move_type: str,
                           incorrect_draft: int = None, has_takeback: bool = None,
                           additional_draw_decider: bool = False) -> None:
        """
        Track context for specific move types (draft and draw moves).
        
        Args:
            card_stats: Card statistics dictionary to update
            replay_id: ID of the current replay
            moves: List of all moves in the game
            current_index: Index of the current move
            move_type: Type of the current move
            incorrect_draft: Draft number that was corrected (if applicable)
            has_takeback: Whether there was a takeback between pass and draft (for draft moves)
            additional_draw_decider: Whether this draw move was decided on a bigger number of moves (6 previous moves)
        """
        # Track context for draft moves, draw moves, and other moves
        if not (move_type.startswith("draft") or 
                move_type == "draw" or
                move_type == "draw_prelude" or
                move_type == "draw_placement" or 
                move_type == "draw_draft_buy" or
                additional_draw_decider or 
                move_type == "other"):
            return
            
        current_move = moves[current_index]
        
        # Get previous moves for context
        prev_3_move = moves[current_index-3] if current_index > 2 else None
        prev_4_move = moves[current_index-4] if current_index > 3 else None
        
        context_data = {
            'replay_id': replay_id,
            'move_number': current_move.get('move_number', 0),
            'generation': current_move.get('game_state', {}).get('generation', 0),
            'current_move': {
                'description': current_move.get('description', ''),
                'action_type': current_move.get('action_type', '')
            }
        }
        
        # Add incorrect_draft field if it exists (for draft moves)
        if move_type.startswith("draft") and incorrect_draft is not None:
            context_data['incorrect_draft'] = incorrect_draft
        
        # Add draft-specific fields if this is a draft move
        if move_type.startswith("draft"):
            context_data['draft_type'] = move_type
            context_data['has_takeback'] = has_takeback
        
        # Add additional_draw_decider flag if this is a draw move with extended context
        if additional_draw_decider:
            context_data['additional_draw_decider'] = True
        
        # Add previous moves data
        context_data.update({
            'move_type': move_type,
            'prev_move': {
                'description': moves[current_index-1].get('description', '') if current_index > 0 else '',
                'action_type': moves[current_index-1].get('action_type', '') if current_index > 0 else ''
            },
            'prev_prev_move': {
                'description': moves[current_index-2].get('description', '') if current_index > 1 else '',
                'action_type': moves[current_index-2].get('action_type', '') if current_index > 1 else ''
            },
            'prev_3_move': {
                'description': prev_3_move.get('description', '') if prev_3_move else '',
                'action_type': prev_3_move.get('action_type', '') if prev_3_move else ''
            },
            'prev_4_move': {
                'description': prev_4_move.get('description', '') if prev_4_move else '',
                'action_type': prev_4_move.get('action_type', '') if prev_4_move else ''
            }
        })
        
        if move_type.startswith("draft"):
            if has_takeback:
                if replay_id not in card_stats['draft_takeback_context']:
                    card_stats['draft_takeback_context'][replay_id] = []
                card_stats['draft_takeback_context'][replay_id].append(context_data)
            else:
                if replay_id not in card_stats['draft_no_takebacks_context']:
                    card_stats['draft_no_takebacks_context'][replay_id] = []
                card_stats['draft_no_takebacks_context'][replay_id].append(context_data)
        elif move_type == "draw_draft_buy":
            if replay_id not in card_stats['draw_draft_buy_context']:
                card_stats['draw_draft_buy_context'][replay_id] = []
            card_stats['draw_draft_buy_context'][replay_id].append(context_data)
        elif move_type == "draw" or move_type == "draw_placement" or move_type == "draw_prelude" or additional_draw_decider:
            if replay_id not in card_stats['draw_context']:
                card_stats['draw_context'][replay_id] = []
            card_stats['draw_context'][replay_id].append(context_data)
        elif move_type == "other":
            if replay_id not in card_stats['other_context']:
                card_stats['other_context'][replay_id] = []
            card_stats['other_context'][replay_id].append(context_data)

    def _calculate_final_stats(self, card_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate and process final statistics for card analysis.
        
        Args:
            card_stats: Raw card statistics dictionary
            
        Returns:
            Processed card statistics with final calculations and formatting
        """
        # Calculate kept play rate
        if card_stats['kept_in_starting_hand'] > 0:
            card_stats['play_to_keep_rate'] = round(card_stats['kept_and_played'] / card_stats['kept_in_starting_hand'], 4)
        
        # Calculate keep rate (how often card is kept when seen in starting hand)
        if card_stats['seen_methods'].get('starting_hand', 0) > 0:
            card_stats['keep_rate'] = round(card_stats['kept_in_starting_hand'] / card_stats['seen_methods']['starting_hand'], 4)
        else:
            card_stats['keep_rate'] = 0
        
        # Convert counters to sorted dictionaries for readability
        card_stats['drawn_by_generation'] = dict(sorted(card_stats['drawn_by_generation'].items()))
        card_stats['played_by_generation'] = dict(sorted(card_stats['played_by_generation'].items()))
        card_stats['draw_methods'] = dict(sorted(card_stats['draw_methods'].items()))
        card_stats['seen_methods'] = dict(sorted(card_stats['seen_methods'].items()))
        card_stats['other_stats'] = dict(sorted(card_stats['other_stats'].items()))
        card_stats['draw_free'] = dict(sorted(card_stats['draw_free'].items()))
        card_stats['draw_and_buy'] = dict(sorted(card_stats['draw_and_buy'].items()))
        card_stats['draw_for_2'] = dict(sorted(card_stats['draw_for_2'].items()))
        
        # Convert drawn_and_played_by_gen to count format
        drawn_played_counts = {}
        for drawn_gen, played_gen in card_stats['drawn_and_played_by_gen']:
            key = f"({drawn_gen},{played_gen})"
            drawn_played_counts[key] = drawn_played_counts.get(key, 0) + 1
        
        # Convert drawn_not_played_by_gen to count format
        drawn_not_played_counts = {}
        for drawn_gen in card_stats['drawn_not_played_by_gen']:
            drawn_not_played_counts[drawn_gen] = drawn_not_played_counts.get(drawn_gen, 0) + 1
        
        # Sort by drawn generation first, then by played generation, with zeros at the end
        def sort_key(item):
            key = item[0]  # The key like "(1,2)" or "(None,1)"
            # Extract numbers from the key, handle None values
            parts = key.strip("()").split(",")
            drawn_str, played_str = parts[0], parts[1]
            
            # Handle None values
            drawn = 0 if drawn_str == "None" else int(drawn_str)
            played = 0 if played_str == "None" else int(played_str)
            
            # Put zeros at the end, otherwise sort by drawn then played
            if drawn == 0:
                return (999, played)  # Large number to put zeros at the end
            return (drawn, played)
        
        card_stats['drawn_and_played_by_gen'] = dict(sorted(drawn_played_counts.items(), key=sort_key))
        card_stats['drawn_not_played_by_gen'] = dict(sorted(drawn_not_played_counts.items()))
        
        # Calculate payment statistics
        if card_stats['payment_amounts']:
            # Count the frequency of each payment combination
            payment_combinations = Counter()
            for payment_list in card_stats['payment_amounts']:
                # Convert list to tuple for hashing (Counter requires hashable keys)
                payment_tuple = tuple(payment_list)
                payment_combinations[payment_tuple] += 1
            
            # Convert tuple keys to strings for reliable sorting and JSON compatibility
            payment_distribution = {}
            for payment_tuple, count in payment_combinations.items():
                payment_key = str(payment_tuple)
                payment_distribution[payment_key] = count
            
            card_stats['payment_distribution'] = dict(sorted(payment_distribution.items()))
        else:
            card_stats['payment_distribution'] = {}
        
        # Remove the payment amounts list, keep only the distribution
        if 'payment_amounts' in card_stats:
            del card_stats['payment_amounts']
        
        # Calculate draw conversion ratios
        # Business Contacts: keep vs draw ratio
        business_contacts_draw = card_stats['seen_methods'].get('business_contacts_draw', 0)
        business_contacts_keep = card_stats['draw_methods'].get('draw_business_contacts_keep', 0)
        if business_contacts_draw > 0:
            card_stats['keep_rates']['business_contacts_keep_rate'] = round(business_contacts_keep / business_contacts_draw, 4)
        else:
            card_stats['keep_rates']['business_contacts_keep_rate'] = 0
        
        # Business Network: buy vs draw ratio
        business_network_draw = card_stats['seen_methods'].get('business_network_draw', 0)
        business_network_buy = card_stats['draw_methods'].get('draw_business_network_buy', 0)
        if business_network_draw > 0:
            card_stats['keep_rates']['business_network_buy_rate'] = round(business_network_buy / business_network_draw, 4)
        else:
            card_stats['keep_rates']['business_network_buy_rate'] = 0
        
        # Invention Contest: keep vs draw ratio
        invention_contest_draw = card_stats['seen_methods'].get('invention_contest_draw', 0)
        invention_contest_keep = card_stats['draw_methods'].get('draw_invention_contest_keep', 0)
        if invention_contest_draw > 0:
            card_stats['keep_rates']['invention_contest_keep_rate'] = round(invention_contest_keep / invention_contest_draw, 4)
        else:
            card_stats['keep_rates']['invention_contest_keep_rate'] = 0
        
        # Inventors' Guild: buy vs draw ratio
        inventors_guild_draw = card_stats['seen_methods'].get('inventors_guild_draw', 0)
        inventors_guild_buy = card_stats['draw_methods'].get('draw_inventors_guild_buy', 0)
        if inventors_guild_draw > 0:
            card_stats['keep_rates']['inventors_guild_buy_rate'] = round(inventors_guild_buy / inventors_guild_draw, 4)
        else:
            card_stats['keep_rates']['inventors_guild_buy_rate'] = 0
        
        # Draft ratios: draft_1 and draft_3 vs research draft total
        research_draft_drafted = card_stats['seen_methods'].get('research_draft_drafted', 0)
        research_draft_not_drafted = card_stats['seen_methods'].get('research_draft_not_drafted', 0)
        research_draft_total = research_draft_drafted + research_draft_not_drafted
        
        draft_1_count = card_stats['seen_methods'].get('draft_1', 0)
        draft_3_count = card_stats['seen_methods'].get('draft_3', 0)
        
        if research_draft_total > 0:
            card_stats['keep_rates']['draft_1_rate'] = round(draft_1_count / research_draft_total, 4)
            card_stats['keep_rates']['draft_3_rate'] = round(draft_3_count / research_draft_total, 4)
        else:
            card_stats['keep_rates']['draft_1_rate'] = 0
            card_stats['keep_rates']['draft_3_rate'] = 0
        
        # Calculate new buy rate ratios
        # Card buy through card rate (Business Network + Inventors' Guild buys)
        total_card_buys = (card_stats['draw_methods'].get('draw_business_network_buy', 0) + 
                          card_stats['draw_methods'].get('draw_inventors_guild_buy', 0))
        total_card_draws = (card_stats['seen_methods'].get('business_network_draw', 0) + 
                           card_stats['seen_methods'].get('inventors_guild_draw', 0))
        
        if total_card_draws > 0:
            card_stats['card_buy_through_card_rate'] = round(total_card_buys / total_card_draws, 4)
        else:
            card_stats['card_buy_through_card_rate'] = 0
        
        # Add card_buy_through_card_rate to keep_rates
        card_stats['keep_rates']['card_buy_through_card_rate'] = card_stats['card_buy_through_card_rate']
        
        # Buy to draft rate (overall)
        total_drafts = (card_stats['seen_methods'].get('draft_1', 0) + 
                       card_stats['seen_methods'].get('draft_2', 0) + 
                       card_stats['seen_methods'].get('draft_3', 0) + 
                       card_stats['seen_methods'].get('draft_4', 0))
        total_draft_buys = card_stats['draw_methods'].get('draw_draft_buy', 0)
        
        if total_drafts > 0:
            card_stats['buy_to_draft_rate'] = round(total_draft_buys / total_drafts, 4)
        else:
            card_stats['buy_to_draft_rate'] = 0
        
        # Buy to draft rates for each specific draft number
        draft_1_count = card_stats['seen_methods'].get('draft_1', 0)
        draft_2_count = card_stats['seen_methods'].get('draft_2', 0)
        draft_3_count = card_stats['seen_methods'].get('draft_3', 0)
        draft_4_count = card_stats['seen_methods'].get('draft_4', 0)
        
        # Calculate rates using the specific buy counts for each draft type
        if draft_1_count > 0:
            card_stats['buy_to_draft_1_rate'] = round(card_stats['draft_1_buys'] / draft_1_count, 4)
        else:
            card_stats['buy_to_draft_1_rate'] = 0
            
        if draft_2_count > 0:
            card_stats['buy_to_draft_2_rate'] = round(card_stats['draft_2_buys'] / draft_2_count, 4)
        else:
            card_stats['buy_to_draft_2_rate'] = 0
            
        if draft_3_count > 0:
            card_stats['buy_to_draft_3_rate'] = round(card_stats['draft_3_buys'] / draft_3_count, 4)
        else:
            card_stats['buy_to_draft_3_rate'] = 0
            
        if draft_4_count > 0:
            card_stats['buy_to_draft_4_rate'] = round(card_stats['draft_4_buys'] / draft_4_count, 4)
        else:
            card_stats['buy_to_draft_4_rate'] = 0
        
        # Calculate play rate ratios
        # Play to buy during game rate
        if card_stats['total_games_when_bought_during_game'] > 0:
            card_stats['play_to_buy_during_game_rate'] = round(card_stats['plays_when_bought_during_game'] / card_stats['total_games_when_bought_during_game'], 4)
        else:
            card_stats['play_to_buy_during_game_rate'] = 0
        
        # Play to buy overall rate (during game + starting hand)
        total_buy_games = card_stats['total_games_when_bought_during_game'] + card_stats['kept_in_starting_hand']
        if total_buy_games > 0:
            card_stats['play_to_buy_overall_rate'] = round(card_stats['plays_when_bought_overall'] / total_buy_games, 4)
        else:
            card_stats['play_to_buy_overall_rate'] = 0
        
        # Play to draw rate (excluding buy methods and starting hand)
        # Count games where card was drawn (excluding buy methods and starting hand)
        draw_games_count = 0
        for method, count in card_stats['draw_methods'].items():
            if method not in BUY_METHODS and method != "draw_start":
                draw_games_count += count
        
        if draw_games_count > 0:
            card_stats['play_to_draw_for_free_rate'] = round(card_stats['plays_when_drawn_for_free'] / draw_games_count, 4)
        else:
            card_stats['play_to_draw_for_free_rate'] = 0
        
        # Play per option rate (when card was seen)
        if card_stats['total_games_when_seen'] > 0:
            card_stats['play_per_option_rate'] = round(card_stats['total_games_when_played'] / card_stats['total_games_when_seen'], 4)
        else:
            card_stats['play_per_option_rate'] = 0
        
        # Play per card in hand rate (when card was drawn)
        if card_stats['total_games_when_with_card_in_hand'] > 0:
            card_stats['play_per_card_in_hand_rate'] = round(card_stats['total_games_when_played'] / card_stats['total_games_when_with_card_in_hand'], 4)
        else:
            card_stats['play_per_card_in_hand_rate'] = 0
        
        # Check for multiple draws
        card_stats['multiple_draws_replay_ids'] = list(card_stats['multiple_draws_games'].keys())
        
        # Calculate player performance statistics
        def calc_win_rate(stats, win_key, total_key):
            total = stats.get(total_key, 0)
            return round((stats.get(win_key, 0) / total) * 100, 4) if total > 0 else 0

        def calc_average_elo(elo_values):
            """Calculate average ELO from a list of values."""
            return round(sum(elo_values) / len(elo_values), 4) if elo_values else 0

        if card_stats['total_games_analyzed'] > 0:
            # Map of result key -> (win_key, total_key)
            percentage_fields = {
                'win_rate_overall': ('win_count', 'total_games_with_card'),
                'win_rate_when_seen': ('win_count_when_seen', 'total_games_when_seen'),
                'win_rate_when_drawn': ('win_count_when_drawn', 'total_games_when_with_card_in_hand'),
                'win_rate_when_bought_during_game': ('win_count_when_bought_during_game', 'total_games_when_bought_during_game'),
                'win_rate_when_played': ('win_count_when_played', 'total_games_when_played'),
                'win_rate_with_prelude': ('wins_with_prelude', 'games_with_prelude'),
                'win_rate_without_prelude': ('wins_without_prelude', 'games_without_prelude')
            }

            for out_key, (win_key, total_key) in percentage_fields.items():
                card_stats[out_key] = calc_win_rate(card_stats, win_key, total_key)
                        
            # Calculate average ELO gain using actual values (overall)
            card_stats['average_elo_gain'] = calc_average_elo(card_stats['actual_elo_values'])
            
            # Calculate average ELO rating at game start (overall)
            card_stats['average_elo'] = calc_average_elo(card_stats['game_ranks'])
            
            # Calculate average ELO gains for each specific case
            card_stats['average_elo_gain_when_seen'] = calc_average_elo(card_stats['elo_values_when_seen'])
            card_stats['average_elo_gain_when_drawn'] = calc_average_elo(card_stats['elo_values_when_drawn'])
            card_stats['average_elo_gain_when_bought_during_game'] = calc_average_elo(card_stats['elo_values_when_bought_during_game'])
            card_stats['average_elo_gain_when_played'] = calc_average_elo(card_stats['elo_values_when_played'])
            
            # Calculate average ELO ratings at game start for each specific case
            card_stats['average_elo_when_seen'] = calc_average_elo(card_stats['game_ranks_when_seen'])
            card_stats['average_elo_when_drawn'] = calc_average_elo(card_stats['game_ranks_when_drawn'])
            card_stats['average_elo_when_bought_during_game'] = calc_average_elo(card_stats['game_ranks_when_bought_during_game'])
            card_stats['average_elo_when_played'] = calc_average_elo(card_stats['game_ranks_when_played'])
        else:
            card_stats['win_rate_overall'] = 0
            card_stats['win_rate_when_seen'] = 0
            card_stats['win_rate_when_drawn'] = 0
            card_stats['win_rate_when_bought_during_game'] = 0
            card_stats['win_rate_when_played'] = 0
            card_stats['average_elo_gain'] = 0
            card_stats['average_elo'] = 0
            # Set all case-specific ELO averages to 0
            card_stats['average_elo_gain_when_seen'] = 0
            card_stats['average_elo_gain_when_drawn'] = 0
            card_stats['average_elo_gain_when_bought_during_game'] = 0
            card_stats['average_elo_gain_when_played'] = 0
            card_stats['average_elo_when_seen'] = 0
            card_stats['average_elo_when_drawn'] = 0
            card_stats['average_elo_when_bought_during_game'] = 0
            card_stats['average_elo_when_played'] = 0
        
        # Reorder card_stats to put statistics above moves
        reordered_stats = {
            'card_name': card_stats['card_name'],
            'total_games_analyzed': card_stats['total_games_analyzed'],
            'total_games_with_card': card_stats['total_games_with_card'],
            'seen_count': card_stats['total_games_when_seen'],
            'drawn_count': card_stats['drawn_count'],
            'played_count': card_stats['played_count'],
            'win_count_by_case': {
                'overall': card_stats['win_count'],
                'when_seen': card_stats['win_count_when_seen'],
                'when_drawn': card_stats['win_count_when_drawn'],
                'when_bought_during_game': card_stats['win_count_when_bought_during_game'],
                'when_played': card_stats['win_count_when_played']
            },
            'win_rate_by_case': {
                'overall': card_stats['win_rate_overall'],
                'when_seen': card_stats['win_rate_when_seen'],
                'when_drawn': card_stats['win_rate_when_drawn'],
                'when_bought_during_game': card_stats['win_rate_when_bought_during_game'],
                'when_played': card_stats['win_rate_when_played']
            },
            # Case-specific ELO metrics
            'elo_metrics_by_case': {
                'overall': {
                    'average_elo_gain': card_stats['average_elo_gain'],
                    'average_elo': card_stats['average_elo']
                },
                'when_seen': {
                    'average_elo_gain': card_stats['average_elo_gain_when_seen'],
                    'average_elo': card_stats['average_elo_when_seen']
                },
                'when_drawn': {
                    'average_elo_gain': card_stats['average_elo_gain_when_drawn'],
                    'average_elo': card_stats['average_elo_when_drawn']
                },
                'when_bought_during_game': {
                    'average_elo_gain': card_stats['average_elo_gain_when_bought_during_game'],
                    'average_elo': card_stats['average_elo_when_bought_during_game']
                },
                'when_played': {
                    'average_elo_gain': card_stats['average_elo_gain_when_played'],
                    'average_elo': card_stats['average_elo_when_played']
                }
            },
            # Prelude statistics
            'prelude_stats': {
                'games_with_prelude': card_stats['games_with_prelude'],
                'games_without_prelude': card_stats['games_without_prelude'],
                'win_rate_with_prelude': card_stats['win_rate_with_prelude'],
                'win_rate_without_prelude': card_stats['win_rate_without_prelude']
            },
            # Starting hand statistics
            'starting_hand_stats': {
                'kept_in_starting_hand': card_stats['kept_in_starting_hand'],
                'kept_and_played': card_stats['kept_and_played'],
                'kept_but_not_played': card_stats['kept_but_not_played'],
                'play_to_keep_rate': card_stats.get('play_to_keep_rate', 0),
                'keep_rate': card_stats.get('keep_rate', 0)
            },
            # Draft and buy statistics
            'draft_buy_stats': {
                'draft_1_buys': card_stats['draft_1_buys'],
                'draft_2_buys': card_stats['draft_2_buys'],
                'draft_3_buys': card_stats['draft_3_buys'],
                'draft_4_buys': card_stats['draft_4_buys'],
                'buy_to_draft_rate': card_stats['buy_to_draft_rate'],
                'buy_to_draft_1_rate': card_stats['buy_to_draft_1_rate'],
                'buy_to_draft_2_rate': card_stats['buy_to_draft_2_rate'],
                'buy_to_draft_3_rate': card_stats['buy_to_draft_3_rate'],
                'buy_to_draft_4_rate': card_stats['buy_to_draft_4_rate']
            },
            # Play rate statistics
            'play_rate_stats': {
                'play_to_buy_during_game_rate': card_stats['play_to_buy_during_game_rate'],
                'play_to_buy_overall_rate': card_stats['play_to_buy_overall_rate'],
                'play_to_draw_for_free_rate': card_stats['play_to_draw_for_free_rate'],
                'play_per_option_rate': card_stats['play_per_option_rate'],
                'play_per_card_in_hand_rate': card_stats['play_per_card_in_hand_rate'],
                'plays_when_bought_during_game': card_stats['plays_when_bought_during_game'],
                'plays_when_bought_overall': card_stats['plays_when_bought_overall'],
                'plays_when_drawn_for_free': card_stats['plays_when_drawn_for_free']
            },
            'keep_rates': card_stats.get('keep_rates', {}),
            'draw_methods': card_stats['draw_methods'],
            'seen_methods': card_stats['seen_methods'],
            'payment_distribution': card_stats.get('payment_distribution', {}),
            'other_stats': card_stats['other_stats'],
            'elo_gains': {
                '-19 and down': card_stats['elo_gains']['-19 and down'],
                '-17 to -18': card_stats['elo_gains']['-17 to -18'],
                '-15 to -16': card_stats['elo_gains']['-15 to -16'],
                '-13 to -14': card_stats['elo_gains']['-13 to -14'],
                '-11 to -12': card_stats['elo_gains']['-11 to -12'],
                '-9 to -10': card_stats['elo_gains']['-9 to -10'],
                '-7 to -8': card_stats['elo_gains']['-7 to -8'],
                '-5 to -6': card_stats['elo_gains']['-5 to -6'],
                '-3 to -4': card_stats['elo_gains']['-3 to -4'],
                '-1 to -2': card_stats['elo_gains']['-1 to -2'],
                '0': card_stats['elo_gains']['0'],
                '1 to 2': card_stats['elo_gains']['1 to 2'],
                '3 to 4': card_stats['elo_gains']['3 to 4'],
                '5 to 6': card_stats['elo_gains']['5 to 6'],
                '7 to 8': card_stats['elo_gains']['7 to 8'],
                '9 to 10': card_stats['elo_gains']['9 to 10'],
                '11 to 12': card_stats['elo_gains']['11 to 12'],
                '13 to 14': card_stats['elo_gains']['13 to 14'],
                '15 to 16': card_stats['elo_gains']['15 to 16'],
                '17 to 18': card_stats['elo_gains']['17 to 18'],
                '19 and up': card_stats['elo_gains']['19 and up']
            },
            'drawn_by_generation': card_stats['drawn_by_generation'],
            'played_by_generation': card_stats['played_by_generation'],
            'draw_free': card_stats['draw_free'],
            'draw_and_buy': card_stats['draw_and_buy'],
            'draw_for_2': card_stats['draw_for_2'],
            'drawn_and_played_by_gen': card_stats['drawn_and_played_by_gen'],
            'drawn_not_played_by_gen': card_stats['drawn_not_played_by_gen'],
            'player_corporations': card_stats['player_corporations'],
            'multiple_draws_replay_ids': card_stats.get('multiple_draws_replay_ids', []),
            'multiple_plays_replay_ids': card_stats.get('multiple_plays_replay_ids', []),
            'multiple_draws_games': card_stats['multiple_draws_games'],
            'moves_card_seen_more_than_once': card_stats['moves_card_seen_more_than_once'],
            'played_but_not_drawn_ids': card_stats['played_but_not_drawn_ids'],
            # Separately
            'draft_takeback_context': card_stats['draft_takeback_context'], 
            'draft_no_takebacks_context': card_stats['draft_no_takebacks_context'],
            'draw_context': card_stats['draw_context'], 
            'draw_draft_buy_context': card_stats['draw_draft_buy_context'],
            'other_context': card_stats['other_context'],
            'game_moves_by_card': card_stats['game_moves_by_card'],
            'draw_draft_buy_without_draft_ids': card_stats['draw_draft_buy_without_draft_ids'],
        }
        
        return reordered_stats

    def _analyze_player_performance(self, game: Dict, player_perspective: str, card_stats: Dict[str, Any],
                                   game_with_card_besides_reveal: bool = False, game_has_draw_move: bool = False,
                                   game_has_buy_move: bool = False, game_has_play_move: bool = False) -> None:
        """
        Analyze player_perspective performance for a specific game.
        
        Args:
            game: Game data dictionary
            player_perspective: Player ID to analyze
            card_stats: Card statistics dictionary to update
            game_with_card_besides_reveal: Whether the card was seen (excluding reveal)
            game_has_draw_move: Whether this game has a draw move
            game_has_buy_move: Whether this game has a buy move
            game_has_play_move: Whether this game has a play move
        """
        winner = game.get('winner', 'unknown')
        players = game.get('players', {})
        
        # Track prelude status for this game
        prelude_on = game.get('prelude_on', False)
        if prelude_on:
            card_stats['games_with_prelude'] += 1
        else:
            card_stats['games_without_prelude'] += 1
        
        # Find player_perspective player data
        player_perspective_data = None
        for player_id, player_data in players.items():
            if player_id == player_perspective:
                player_perspective_data = player_data
                break
        
        # Analyze player_perspective performance
        if player_perspective_data:
            player_name = player_perspective_data.get('player_name', 'unknown')
            
            # Track corporation used by player_perspective
            corporation = player_perspective_data.get('corporation', 'unknown')
            card_stats['player_corporations'][corporation] += 1
            
            # Check if player_perspective won
            if player_name == winner:
                card_stats['win_count'] += 1
                
                # Track wins for different game types
                if game_with_card_besides_reveal:
                    card_stats['win_count_when_seen'] += 1
                if game_has_draw_move:
                    card_stats['win_count_when_drawn'] += 1
                if game_has_buy_move:
                    card_stats['win_count_when_bought_during_game'] += 1
                if game_has_play_move:
                    card_stats['win_count_when_played'] += 1
                
                # Track wins by prelude status
                if prelude_on:
                    card_stats['wins_with_prelude'] += 1
                else:
                    card_stats['wins_without_prelude'] += 1
            
            # Get ELO gain for player_perspective
            elo_data = player_perspective_data.get('elo_data')
            game_rank_change = 0  # Default value
            game_rank = 0  # Default value
            if elo_data and isinstance(elo_data, dict):
                game_rank_change = elo_data.get('game_rank_change', 0)
                game_rank = elo_data.get('game_rank', 0)  # Get the player's ELO rating at game start
                
                # Track ELO gain distribution
                card_stats['elo_gains'][self._get_elo_bucket(game_rank_change)] += 1
                card_stats['actual_elo_values'].append(game_rank_change) # Store actual value
                card_stats['game_ranks'].append(game_rank) # Store actual ELO rating
                
                # Track ELO values separately for each case
                if game_with_card_besides_reveal:
                    card_stats['elo_values_when_seen'].append(game_rank_change)
                    card_stats['game_ranks_when_seen'].append(game_rank)
                if game_has_draw_move:
                    card_stats['elo_values_when_drawn'].append(game_rank_change)
                    card_stats['game_ranks_when_drawn'].append(game_rank)
                if game_has_buy_move:
                    card_stats['elo_values_when_bought_during_game'].append(game_rank_change)
                    card_stats['game_ranks_when_bought_during_game'].append(game_rank)
                if game_has_play_move:
                    card_stats['elo_values_when_played'].append(game_rank_change)
                    card_stats['game_ranks_when_played'].append(game_rank)

    def tfm_card_analyzer(self, card_name: str) -> Dict[str, Any]:
        """
        ENTRY POINT OF THE ANALYZER
        Analyze complete history of a specific card across all games.
        
        Args:
            card_name: Name of the card to analyze
            
        Returns:
            Dictionary with comprehensive card statistics
        """
        if not self.games_data:
            return {}
        
        card_stats = self._initialize_card_stats(card_name)
        
        for game in tqdm(self.games_data, desc=f"Analyzing {card_name}", unit="game"):
            player_perspective = game.get('player_perspective', '')
            moves = game.get('moves', [])
            replay_id = game.get('replay_id', '')
            
            if not moves or not player_perspective:
                continue
            
            card_stats['total_games_analyzed'] += 1
            
            # Track card state for this game
            kept_in_hand = self._check_kept_in_starting_hand(moves, player_perspective, card_name)
            played_in_game = False
            
            # Track the last draw occurrence for this game
            last_draw_generation = None
            last_draw_stats_key = None
            played_generation = None
            
            # Track draft-to-buy relationships for this game
            game_draft_sequence = []  # Track draft moves in order
            game_buy_moves = []       # Track buy moves
            
            if kept_in_hand:
                card_stats['kept_in_starting_hand'] += 1
            
            # Track all moves for this game to detect multiple draws
            game_moves = []
            
            # Track if this game has multiple plays
            play_count = 0
            
            # Collect all player names in this game to check for wrong card attribution
            player_names = {}  # player_id: player_name mapping
            players = game.get('players', {})
            player_perspective_name = ""
            opponent_name = ""
            for player_id, player_data in players.items():
                if isinstance(player_data, dict):
                    player_name = player_data.get('player_name', '')
                    if player_name:
                        player_names[player_id] = player_name
                        # Get the name for player_perspective
                        if player_id == player_perspective:
                            player_perspective_name = player_name
                        else:
                            opponent_name = player_name
            
            # Check if card appears in starting hand data (when MUST_INCLUDE_STARTING_HAND is true)
            card_in_starting_hand = False
            if MUST_INCLUDE_STARTING_HAND:
                for player_data in players.values():
                    if isinstance(player_data, dict) and 'starting_hand' in player_data:
                        starting_hand = player_data['starting_hand']
                        if isinstance(starting_hand, dict):
                            # Check project cards in starting hand - use exact name matching to avoid false positives
                            project_cards = starting_hand.get('project_cards', [])
                            if any(card_name == str(card) for card in project_cards):
                                card_in_starting_hand = True
                                break
            
            # If card was found in starting hand, add it as a seen method
            if card_in_starting_hand:
                card_stats['seen_methods']['starting_hand'] += 1
            
            # Find all draws and plays
            for i, move in enumerate(moves):
                if card_name not in move.get('description', ''):
                    continue
                    
                description = move.get('description', '')
                if move.get('player_id') != player_perspective and move.get('action_type') != 'pass':
                    # Skip if description does not involve our player
                    player_actions = (f"{player_perspective_name} {verb} {card_name}"
                                    for verb in ("draws", "plays", "keeps"))
                    
                    if not any(action in description for action in player_actions):
                        if not "You " in description:
                            continue
                
                action_type = move.get('action_type', '')
                card_played = move.get('card_played', '')
                game_state = move.get('game_state', {})
                generation = game_state.get('generation', 0)
                
                # Check for draws (count each game only once)
                move_type = "other"
                
                # Initialize draft-related variables
                has_takeback = False
                incorrect_draft = None

                # Prepare descriptions and action types for pattern matching
                # Handle cases where prev_description or prev_action_type might be empty
                prev_move = moves[i-1] if i > 0 else None
                prev_prev_move = moves[i-2] if i > 1 else None
                next_move = moves[i+1] if i < len(moves) - 1 else None
                next_2_move = moves[i+2] if i < len(moves) - 2 else None
                prev_description = prev_move.get('description', '') if prev_move else ''
                prev_action_type = prev_move.get('action_type', '') if prev_move else ''
                prev_prev_description = prev_prev_move.get('description', '') if prev_prev_move else ''
                prev_prev_action_type = prev_prev_move.get('action_type', '') if prev_prev_move else ''
                next_description = next_move.get('description', '') if next_move else ''
                next_2_description = next_2_move.get('description', '') if next_2_move else ''
                next_player_id = next_move.get('player_id') if next_move else None

                # Clean descriptions of confusing card patterns
                next_description = self._strip_confusing_patterns(next_description, card_name)
                next_2_description = self._strip_confusing_patterns(next_2_description, card_name)

                descriptions = [
                    description,
                    prev_description if prev_description else "",
                    prev_prev_description if prev_prev_description else ""
                ]
                action_types = [
                    action_type,
                    prev_action_type if prev_action_type else "",
                    prev_prev_action_type if prev_prev_action_type else "",
                ]
                
                # Use the new method to detect and determine the draw type
                move_type = self._detect_draw_move(
                    card_name, descriptions, action_types, 
                    next_description, next_2_description, next_player_id, player_perspective, 
                    player_perspective_name, opponent_name, generation
                )

                # If the method returned "skip_wrong_attribution", skip this move
                if move_type == "skip_wrong_attribution":
                    continue

                # Track if this draw move was decided on a bigger number of moves (6 previous moves)
                additional_draw_decider = False
                
                if move_type in ("draw", "draw_placement"):
                    # Offsets to check progressively
                    offsets_groups = [
                        [3, 4],
                        [5, 6],
                        [7, 8, 9]
                    ]
                    
                    for offsets in offsets_groups:
                        for offset in offsets:
                            if i > offset - 1:
                                descriptions.append(moves[i - offset].get('description', ''))
                                action_types.append(moves[i - offset].get('action_type', ''))
                        
                        move_type = self._detect_draw_move(
                            card_name, descriptions, action_types, 
                            next_description, next_2_description, next_player_id,
                            player_perspective, player_perspective_name,
                            opponent_name, generation
                        )
                        
                        if move_type not in ("draw", "draw_placement", "draw_prelude"): # undecided types
                            break

                    # Mark this as a draw move that needed additional context
                    additional_draw_decider = True

                if move_type == "draft":
                    draft_info = self._determine_draft_type(moves, i, player_perspective, card_name, player_perspective_name, opponent_name)
                    move_type = draft_info["draft_type"]
                    has_takeback = draft_info.get("has_takeback", False)
                    incorrect_draft = draft_info.get("incorrect_draft")
                    
                    # Track this draft move for buy relationship analysis
                    game_draft_sequence.append({
                        'draft_type': move_type,
                        'move_number': move.get('move_number', 0),
                        'generation': generation
                    })
                
                # Track buy moves
                if move_type == "draw_draft_buy":
                    game_buy_moves.append({
                        'move_number': move.get('move_number', 0),
                        'generation': generation
                    })
                
                # Track the last draw occurrence instead of immediately counting
                if move_type.startswith("draw"):
                    last_draw_generation = generation
                    last_draw_stats_key = move_type

                # Count seen methods immediately (they should always count)
                elif move_type != "other":
                    card_stats['seen_methods'][move_type] += 1
                
                # Check for plays (count each game only once)
                paid_amount = None
                if (not played_in_game and action_type == 'play_card' and (card_played == card_name or card_played == "Eccentric Sponsor")
                    and not "undoes" in next_description and not f"{opponent_name} plays card {card_name}" in description):
                    played_in_game = True
                    played_generation = generation
                    move_type = "play"
                    card_stats['played_by_generation'][generation] += 1
                    card_stats['played_count'] += 1
                    play_count += 1
                    paid_amount = self._process_play_payment(description, card_stats)
                
                # Other
                if move_type == "other":
                    move_type = self._classify_other_move_type(description, action_type, next_description, next_2_description, card_name, opponent_name)
                    card_stats['other_stats'][move_type] += 1
                
                # Track context for specific move types
                self._track_move_context(card_stats, replay_id, moves, i, move_type, incorrect_draft, has_takeback, additional_draw_decider)

                # Store move
                move_data = {
                    'description': move.get('description', ''),
                    'generation': generation,
                    'move_number': move.get('move_number', 0),
                    'action_type': action_type,
                    'move_type': move_type,
                }
                
                # Add payment amount for plays
                if move_type == "play" and paid_amount is not None:
                    move_data['paid'] = paid_amount
                
                # Collect all moves for this game
                game_moves.append(move_data)
                                                    
            # Check for multiple draws in this game
            draw_count = sum(1 for move in game_moves if move['move_type'].startswith('draw'))
            if draw_count > 1:
                card_stats['multiple_draws_games'][replay_id] = game_moves
            
            # Check for multiple plays in this game
            if play_count > 1:
                card_stats['multiple_plays_replay_ids'].append(replay_id)
            
            if kept_in_hand and played_in_game:
                card_stats['kept_and_played'] += 1
                card_stats['drawn_and_played_by_gen'].append((last_draw_generation, played_generation))
            elif kept_in_hand and not played_in_game:
                card_stats['kept_but_not_played'] += 1
            
            # After processing all moves in the game, classify research_draft moves
            self._post_process_research_draft_moves(card_stats, game_moves)
                        
            # Check for 2 draft moves close together (< 30 moves apart)
            self._handle_close_draft_moves(card_stats, game_moves, replay_id)

            # After processing all moves in the game, analyze draft-to-buy relationships
            self._analyze_draft_to_buy_relationships(card_stats, game_draft_sequence, game_buy_moves, replay_id)
            
            # Process game draw statistics using the new function
            self._process_game_draw_statistics(card_stats, game_moves, replay_id, last_draw_stats_key, last_draw_generation, card_in_starting_hand)
            
            # Count games where card appeared in any way
            if any(not move['move_type'].startswith('other') for move in game_moves):  # Check for actual moves with this card
                
                card_stats['total_games_with_card'] += 1
                game_key = f"{replay_id}_{player_perspective}"
                card_stats['game_moves_by_card'][game_key] = game_moves
                # Track game types and plays using the new function
                game_with_card_besides_reveal, game_has_any_draw_move, game_has_buy_move, game_has_play_move = self._track_game_types_and_plays(
                    card_stats, game_moves, kept_in_hand, card_in_starting_hand)

                # Determine winner and analyze player_perspective performance
                self._analyze_player_performance(game, player_perspective, card_stats,
                                                game_with_card_besides_reveal, game_has_any_draw_move,
                                                game_has_buy_move, game_has_play_move)
            
            # Track drawn and played generations
            if last_draw_generation is not None:
                if played_generation is not None:
                    # Card was both drawn and played
                    card_stats['drawn_and_played_by_gen'].append((last_draw_generation, played_generation))
                else:
                    # Card was drawn but not played
                    card_stats['drawn_not_played_by_gen'].append(last_draw_generation)
            elif played_generation is not None:
                # Card was played but not drawn - this shouldn't happen
                print(f"WARNING: Card '{card_name}' was played in generation {played_generation} but not drawn in game {replay_id}")
                card_stats['drawn_and_played_by_gen'].append((0, played_generation))
                # Keep the context for played-but-not-drawn cards
                card_stats['played_but_not_drawn_ids'].append(replay_id)
        
        # Calculate final statistics and return processed results
        return self._calculate_final_stats(card_stats)
        
    def save_card_analysis(self, card_name: str, output_dir: str = "analysis_output"):
        """
        Save detailed card analysis to JSON file.
        
        Args:
            card_name: Name of the card to analyze
            output_dir: Directory to save output files
        """
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        # Create context subfolder
        context_path = output_path / "context"
        context_path.mkdir(exist_ok=True)
        
        card_stats = self.tfm_card_analyzer(card_name)
        
        # Extract moves data before saving main analysis
        moves_data = card_stats.pop('game_moves_by_card', {})
        
        # Extract context data before saving main analysis
        context_data = {
            'draft_takeback_context': card_stats.pop('draft_takeback_context', {}),
            'draft_no_takebacks_context': card_stats.pop('draft_no_takebacks_context', {}),
            'draw_context': card_stats.pop('draw_context', {}),
            'draw_draft_buy_context': card_stats.pop('draw_draft_buy_context', {}),
            'other_context': card_stats.pop('other_context', {})
        }
        
        # Save main analysis to JSON (without moves data and context data)
        filename = f"card_analysis_{card_name.replace(' ', '_').replace('"', '')}.json"
        with open(output_path / filename, 'w', encoding='utf-8') as f:
            json.dump(card_stats, f, indent=2, default=str)
        
        # Show main file size
        main_file_path = output_path / filename
        main_size_mb = main_file_path.stat().st_size / (1024 * 1024)
        print(f"Card analysis saved to: {output_path}/{filename} (size: {main_size_mb:.1f} MB)")
        
        # Save game moves to separate file
        if moves_data:
            moves_filename = f"game_moves_{card_name.replace(' ', '_').replace('"', '')}.json"
            with open(output_path / moves_filename, 'w', encoding='utf-8') as f:
                json.dump(moves_data, f, indent=2, default=str)
            moves_file_path = output_path / moves_filename
            moves_size_mb = moves_file_path.stat().st_size / (1024 * 1024)
            print(f"Game moves saved to: {output_path}/{moves_filename} (size: {moves_size_mb:.1f} MB)")
        else:
            print(f"No game moves found for card: {card_name}")
        
        # Save context data to separate file in context subfolder
        if any(context_data.values()):  # Check if any context data exists
            context_filename = f"context_{card_name.replace(' ', '_').replace('"', '')}.json"
            with open(context_path / context_filename, 'w', encoding='utf-8') as f:
                json.dump(context_data, f, indent=2, default=str)
            context_file_path = context_path / context_filename
            context_size_mb = context_file_path.stat().st_size / (1024 * 1024)
            print(f"Context data saved to: {context_path}/{context_filename} (size: {context_size_mb:.1f} MB)")
        else:
            print(f"No context data found for card: {card_name}")
        
        return card_stats

    def _post_process_research_draft_moves(self, card_stats: Dict[str, Any], game_moves: list) -> None:
        """
        Post-process research_draft moves to classify them as drafted or not drafted.
        
        Args:
            card_stats: Card statistics dictionary to update
            game_moves: List of moves for the current game
        """
        if 'research_draft' in card_stats['seen_methods'] and card_stats['seen_methods']['research_draft'] > 0:
            # Check if this game has draft_1 or draft_3 moves
            has_draft_1_or_3 = any(
                move['move_type'] in ['draft_1', 'draft_3'] 
                for move in game_moves
            )
            
            if has_draft_1_or_3:
                # This game has both research_draft and draft_1/draft_3
                # Convert research_draft to research_draft_drafted
                card_stats['seen_methods']['research_draft'] -= 1
                card_stats['seen_methods']['research_draft_drafted'] = card_stats['seen_methods'].get('research_draft_drafted', 0) + 1
                
                # Update move_type in game_moves from 'research_draft' to 'research_draft_drafted'
                for move in game_moves:
                    if move['move_type'] == 'research_draft':
                        move['move_type'] = 'research_draft_drafted'
                
            else:
                # This game has research_draft but no draft_1/draft_3
                # Convert research_draft to research_draft_not_drafted
                card_stats['seen_methods']['research_draft'] -= 1
                card_stats['seen_methods']['research_draft_not_drafted'] = card_stats['seen_methods'].get('research_draft_not_drafted', 0) + 1
                
                # Update move_type in game_moves from 'research_draft' to 'research_draft_not_drafted'
                for move in game_moves:
                    if move['move_type'] == 'research_draft':
                        move['move_type'] = 'research_draft_not_drafted'
                
            # Remove research_draft entry if count reaches 0
            if card_stats['seen_methods']['research_draft'] == 0:
                del card_stats['seen_methods']['research_draft']

    def _analyze_draft_to_buy_relationships(self, card_stats: Dict[str, Any], game_draft_sequence: list, game_buy_moves: list, replay_id: str) -> None:
        """
        Analyze relationships between draft moves and subsequent buy moves.
        
        Args:
            card_stats: Card statistics dictionary to update
            game_draft_sequence: List of draft moves in the current game
            game_buy_moves: List of buy moves in the current game
            replay_id: ID of the current replay
        """
        # Check for cases where there are draw_draft_buy moves but no corresponding draft moves
        if game_buy_moves and not game_draft_sequence:
            card_stats['draw_draft_buy_without_draft_ids'].append(replay_id)
            print(f"WARNING: Found draw_draft_buy moves without corresponding draft moves in replay {replay_id}")
        
        if game_draft_sequence and game_buy_moves:
            # For each draft move, find if there's a subsequent buy move
            for draft_move in game_draft_sequence:
                draft_type = draft_move['draft_type']
                draft_move_number = draft_move['move_number']
                
                # Look for buy moves that come after this draft move
                for buy_move in game_buy_moves:
                    if buy_move['move_number'] > draft_move_number:
                        # This buy came after the draft
                        if draft_type == 'draft_1':
                            card_stats['draft_1_buys'] += 1
                        elif draft_type == 'draft_2':
                            card_stats['draft_2_buys'] += 1
                        elif draft_type == 'draft_3':
                            card_stats['draft_3_buys'] += 1
                        elif draft_type == 'draft_4':
                            card_stats['draft_4_buys'] += 1
                        break  # Only count the first buy after this draft

    def _handle_close_draft_moves(self, card_stats: Dict[str, Any], game_moves: list, replay_id: str) -> None:
        """
        Handle cases where there are 2 draft moves close together (< 30 moves apart).
        
        Args:
            card_stats: Card statistics dictionary to update
            game_moves: List of moves for the current game
            replay_id: ID of the current replay
        """
        current_game_draft_moves = [move for move in game_moves if move.get('move_type', '').startswith('draft')]
        if len(current_game_draft_moves) == 2:
            print(f"WARNING: Found 2 draft moves in game {replay_id}!")
            move_numbers = [move.get('move_number', 0) for move in current_game_draft_moves]
            distance = abs(move_numbers[1] - move_numbers[0])
            
            if distance < 30:
                # Find the earlier draft move
                earlier_move_index = 0 if move_numbers[0] < move_numbers[1] else 1
                earlier_move = current_game_draft_moves[earlier_move_index]
                
                # Change the earlier move type to other_takeback_draft in game_moves
                for game_move in game_moves:
                    if (game_move['move_number'] == earlier_move.get('move_number') and 
                        game_move['move_type'].startswith('draft')):
                        game_move['move_type'] = 'other_takeback_draft'
                        print(f"Setting other_takeback_draft for move {game_move.get('move_number', 0)} in game {replay_id}!")
                        break
                
                # Update the stats
                card_stats['other_stats']['other_takeback_draft'] += 1
                
                # Remove the original draft count from seen_methods
                original_draft_type = current_game_draft_moves[earlier_move_index].get('move_type', '')
                if original_draft_type in card_stats['seen_methods']:
                    card_stats['seen_methods'][original_draft_type] -= 1

    def _process_play_payment(self, description: str, card_stats: Dict[str, Any]) -> list:
        """
        Process payment information for a play move.
        Captures all payment amounts (there can be multiple "pays X" instances).
        
        Args:
            description: Current move description
            card_stats: Card statistics dictionary to update
            
        Returns:
            List of payment amounts found
        """
        # Find all payment amounts in the description
        payment_matches = re.findall(r'pays (\d+)', description)
        
        if payment_matches:
            # Convert to integers and preserve original order
            paid_amounts = [int(amount) for amount in payment_matches]
            # Store the list of payment amounts
            card_stats['payment_amounts'].append(paid_amounts)
        else:
            # No payment found - this is a free play (count as empty list)
            paid_amounts = []
            card_stats['payment_amounts'].append(paid_amounts)
        
        return paid_amounts

    def _classify_other_move_type(self, description: str, action_type: str, next_description: str, next_2_description: str, card_name: str, oponnent_name: str) -> str:
        """
        Classify the specific type of "other" move.
        
        Args:
            description: Current move description
            action_type: Current move action type
            next_description: Next move description
            card_name: Name of the card being analyzed
            
        Returns:
            The classified move type string
        """
        if f"immediate effect of {card_name}" in description:
            return "other_immediate_effect"
        elif f"triggered effect of {card_name}" in description:
            return "other_triggered_effect"
        elif f"activates {card_name}" in description:
            return "other_activate"
        elif f"activation effect of {card_name}" in description:
            return "other_activation_effect"
        elif f"places {card_name}" in description or f"places tile {card_name}" in description:
            return "other_place_card"
        elif f"places City on {card_name}" in description or f"places tile City into {card_name}" in description:
            return "other_place_city"
        elif f"copies production box of {card_name}" in description:
            return "other_copy_production_box"
        elif f"removes Microbe from {card_name}" in description:
            return "other_remove_microbe"
        elif f"removes Animal from {card_name}" in description:
            return "other_remove_animal"
        elif f"adds Microbe to {card_name}" in description:
            return "other_add_microbe"
        elif f"adds Animal to {card_name}" in description:
            return "other_add_animal"
        elif f"moves Resource into {card_name}" in description:
            return "other_move_resource"
        elif f"{oponnent_name} plays card {card_name}" in description:
            return "other_opponent_play"
        elif "(Lava Flows)" in description and action_type == "place_tile" and card_name == "Lava Flows":
            return "other_place_lava_and_ocean"
        elif any(
            f"({name})" in description and card_name == name
            for name in ["Lava Flows", "Capital", "Ecological Zone", "Restricted Area", "Nuclear Zone", "Natural Preserve", "Mohole Area", "Industrial Center", "Commercial District"]
        ):
            return "other_place_gain"
        elif "scores" in description:
            return "other_scoring"
        elif "adds Science to" in description:
            return "other_add_science"
        elif "removes Science from" in description:
            return "other_remove_science"
        elif "undoes" in next_description:
            return "other_takeback_undo"
        elif "draws 10 cards" in description:
            return "other_starting_hand"
        elif "takes back their move" in next_description or f"You buy {card_name}" in next_2_description:
            if "You choose corporation" in description:
                return "other_takeback_start"
            elif action_type == "draft_card":
                return "other_takeback_draft"
            elif "You buy" in description:
                return "other_takeback_buy"
            else:
                return "other_takeback"
        elif "You choose corporation" in next_description:
            return "other_takeback_start"
        elif "You draft" in description:
            return "other_takeback_draft"
        else:
            return "other"

    def _track_game_types_and_plays(self, card_stats: Dict[str, Any], game_moves: list, kept_in_hand: bool, card_in_starting_hand: bool) -> tuple[bool, bool, bool]:
        """
        Track different game types and plays for win percentage calculations.
        
        Args:
            card_stats: Card statistics dictionary to update
            game_moves: List of moves for the current game
            kept_in_hand: Whether the card was kept in starting hand
            card_in_starting_hand: Whether the card was found in starting hand data
            
        Returns:
            Tuple of (game_with_card_besides_reveal, game_has_any_draw_move, game_has_buy_move, game_has_play_move)
        """
        game_with_card_besides_reveal = any(((move['move_type'] in card_stats['seen_methods'] and
                                            not move['move_type'].startswith('reveal')) or
                                    move['move_type'] in card_stats['draw_methods'])
                                    for move in game_moves)
        
        # Also check if card was seen in starting hand data
        if card_in_starting_hand:
            game_with_card_besides_reveal = True
        
        game_has_any_draw_move = any(move['move_type'] in card_stats['draw_methods'] for move in game_moves)
        game_has_draw_no_buy_move = any((move['move_type'] in card_stats['draw_methods'] and
                                         move['move_type'] not in BUY_METHODS and move['move_type'] != "draw_start"
                                         ) for move in game_moves)
        game_has_buy_move = any(move['move_type'] in BUY_METHODS for move in game_moves)
        game_has_play_move = any(move['move_type'] == 'play' for move in game_moves)

        if game_with_card_besides_reveal:
            card_stats['total_games_when_seen'] += 1 # card was available to pick
        if game_has_any_draw_move:
            card_stats['total_games_when_with_card_in_hand'] += 1 # card was drawn or bought (including starting hand, when flag is set)
        if game_has_buy_move:
            card_stats['total_games_when_bought_during_game'] += 1 # card was bought during the game
        if game_has_play_move:
            card_stats['total_games_when_played'] += 1
            
        # Track plays under specific conditions for rate calculations
        if game_has_buy_move and game_has_play_move:
            card_stats['plays_when_bought_during_game'] += 1
        if (game_has_buy_move or kept_in_hand) and game_has_play_move:
            card_stats['plays_when_bought_overall'] += 1
        if game_has_draw_no_buy_move and game_has_play_move:
            card_stats['plays_when_drawn_for_free'] += 1
            
        return game_with_card_besides_reveal, game_has_any_draw_move, game_has_buy_move, game_has_play_move

    def _process_game_draw_statistics(self, card_stats: Dict[str, Any], game_moves: list, replay_id: str, 
                                     last_draw_stats_key: str, last_draw_generation: int, card_in_starting_hand: bool) -> None:
        """
        Process draw statistics for a specific game, including multiple seen method detection and draw counting.
        
        Args:
            card_stats: Card statistics dictionary to update
            game_moves: List of moves for the current game
            replay_id: ID of the current replay
            last_draw_stats_key: The key for the last draw method in this game
            last_draw_generation: The generation when the last draw occurred
            card_in_starting_hand: Whether the card was found in starting hand data
        """
        # Check for multiple seen_method moves in this game
        # Count actual moves that are seen methods within the current game
        seen_method_moves = []
        for move in game_moves:
            move_type = move.get('move_type', '')
            if (move_type and 
                move_type in card_stats['seen_methods'] and
                move_type != 'research_draft_drafted'):
                seen_method_moves.append(move)
        
        # Also check if card was seen in starting hand data
        if card_in_starting_hand:
            seen_method_moves.append({'move_type': 'starting_hand', 'description': 'Card found in starting hand data'})
        
        if len(seen_method_moves) > 1:
            # Store the full move data for moves where card was seen more than once
            card_stats['moves_card_seen_more_than_once'][replay_id] = game_moves
        
        # Count only the last draw occurrence for this game
        if last_draw_stats_key:
            card_stats['draw_methods'][last_draw_stats_key] += 1
            card_stats['drawn_by_generation'][last_draw_generation] += 1
            card_stats['drawn_count'] += 1

            if last_draw_stats_key in FREE_DRAW_METHODS:
                card_stats['draw_free'][last_draw_generation] += 1
            
            # Track draws that involve buying by generation
            if last_draw_stats_key in BUY_METHODS:
                card_stats['draw_and_buy'][last_draw_generation] += 1

            # Track draws from Restricted Area by generation
            if last_draw_stats_key == "draw_restricted_area":
                card_stats['draw_for_2'][last_draw_generation] += 1