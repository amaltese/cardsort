from typing import List, Dict, Any, Optional

class SortService:
    @staticmethod
    def get_initial_placements(condition: str, cards: List[Any], starting_categories: List[Any]) -> Dict[str, Any]:
        categories = [cat.name for cat in starting_categories]
        
        # Enforce initial condition requirements
        if condition == "OPEN":
            categories = []  # Open sort starts with no predefined categories
            
        unassigned_cards = [c.card_id for c in cards]
        placements = {cat: [] for cat in categories}
        placements["Unassigned"] = unassigned_cards
        return {
            "categories": categories,
            "placements": placements,
            "category_descriptions": {cat.name: cat.description for cat in starting_categories} if condition != "OPEN" else {}
        }

    @staticmethod
    def move_card(placements: Dict[str, List[str]], card_id: str, target_category: str) -> Dict[str, List[str]]:
        new_placements = {}
        for cat, card_list in placements.items():
            new_placements[cat] = [c for c in card_list if c != card_id]
        
        if target_category not in new_placements:
            new_placements[target_category] = []
        new_placements[target_category].append(card_id)
        return new_placements