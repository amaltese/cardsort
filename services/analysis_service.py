import json
import pandas as pd
from typing import List, Dict, Any, Optional
from database.db import get_connection
from database.models import Card

class AnalysisService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def get_completed_snapshots(self, study_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT snapshot_json FROM participant_sessions
        WHERE study_id = ? AND status = 'completed'
        """, (study_id,))
        rows = cursor.fetchall()
        conn.close()
        
        snapshots = []
        for r in rows:
            if r["snapshot_json"]:
                try:
                    snapshots.append(json.loads(r["snapshot_json"]))
                except Exception:
                    pass
        return snapshots

    @staticmethod
    def _card_context(cards: List[Any]):
        """Use stable card IDs for calculations; labels are only for display."""
        if not cards:
            return [], {}, {}
        if isinstance(cards[0], str):  # Backwards-compatible public method use.
            return cards, {card: card for card in cards}, {card: [card] for card in cards}
        card_ids = [card.card_id for card in cards]
        labels = {card.card_id: card.title for card in cards}
        title_to_ids = {}
        for card in cards:
            title_to_ids.setdefault(card.title, []).append(card.card_id)
        return card_ids, labels, title_to_ids

    def _placements_by_card_id(self, snapshot: Dict[str, Any], card_ids: List[str], title_to_ids: Dict[str, List[str]]):
        stored = snapshot.get("placement_card_ids")
        if stored:
            return {
                category: [card_id for card_id in items if card_id in card_ids]
                for category, items in stored.items()
            }
        # Older records stored titles only. A title maps safely only when it is
        # unique; ambiguous historical records are deliberately not guessed.
        return {
            category: [title_to_ids[item][0] for item in items if len(title_to_ids.get(item, [])) == 1]
            for category, items in snapshot.get("placements", {}).items()
        }

    def get_co_occurrence_matrix(self, study_id: str, cards: List[Any]) -> pd.DataFrame:
        snapshots = self.get_completed_snapshots(study_id)
        card_ids, labels, title_to_ids = self._card_context(cards)
        if not card_ids:
            return pd.DataFrame()
            
        co_matrix = pd.DataFrame(0.0, index=card_ids, columns=card_ids)
        n_participants = len(snapshots)
        
        if n_participants == 0:
            return co_matrix

        for snap in snapshots:
            placements = self._placements_by_card_id(snap, card_ids, title_to_ids)
            for cat_name, items in placements.items():
                valid_cards = [c for c in items if c in card_ids]
                for i in range(len(valid_cards)):
                    for j in range(len(valid_cards)):
                        co_matrix.loc[valid_cards[i], valid_cards[j]] += 1.0

        co_matrix = (co_matrix / n_participants) * 100.0
        return co_matrix.rename(index=labels, columns=labels).round(1)

    def get_card_agreement_summary(self, study_id: str, cards: List[Any]) -> pd.DataFrame:
        snapshots = self.get_completed_snapshots(study_id)
        n_participants = len(snapshots)
        card_ids, labels, title_to_ids = self._card_context(cards)
        
        if n_participants == 0 or not card_ids:
            return pd.DataFrame(columns=["Card Title", "Primary Category", "Agreement %", "Agreement Level"])

        cat_rows = []
        for snap in snapshots:
            placements = self._placements_by_card_id(snap, card_ids, title_to_ids)
            for cat_name, items in placements.items():
                for card in items:
                    if card in card_ids:
                        cat_rows.append({"card": card, "category": cat_name})

        if not cat_rows:
            return pd.DataFrame(columns=["Card Title", "Primary Category", "Agreement %", "Agreement Level"])

        df_cat = pd.DataFrame(cat_rows)
        freq_matrix = pd.crosstab(df_cat["card"], df_cat["category"])

        summary = []
        for card in card_ids:
            if card in freq_matrix.index:
                counts = freq_matrix.loc[card]
                top_cat = str(counts.idxmax())
                top_count = int(counts.max())
                pct = round((top_count / n_participants) * 100, 1)
                
                if pct >= 75:
                    level = "🟢 High Consensus"
                elif pct >= 50:
                    level = "🟡 Moderate Agreement"
                else:
                    level = "🔴 Low / Controversial"
                    
                summary.append({
                    "Card Title": labels[card],
                    "Primary Category": top_cat,
                    "Agreement %": pct,
                    "Agreement Level": level
                })
            else:
                summary.append({
                    "Card Title": labels[card],
                    "Primary Category": "Unassigned",
                    "Agreement %": 0.0,
                    "Agreement Level": "🔴 Unsorted"
                })

        return pd.DataFrame(summary)

    def get_card_category_frequency(self, study_id: str, cards: List[Any]) -> pd.DataFrame:
        snapshots = self.get_completed_snapshots(study_id)
        n_participants = len(snapshots)
        card_ids, labels, title_to_ids = self._card_context(cards)
        
        if n_participants == 0 or not card_ids:
            return pd.DataFrame()

        cat_rows = []
        for snap in snapshots:
            placements = self._placements_by_card_id(snap, card_ids, title_to_ids)
            for cat_name, items in placements.items():
                for card in items:
                    if card in card_ids:
                        cat_rows.append({"card": card, "category": cat_name})

        if not cat_rows:
            return pd.DataFrame()

        df_cat = pd.DataFrame(cat_rows)
        freq_matrix = pd.crosstab(df_cat["card"], df_cat["category"])
        freq_pct = (freq_matrix.div(n_participants, axis=0) * 100).round(1)
        
        # Ensure all study cards are present in index
        for card in card_ids:
            if card not in freq_pct.index:
                freq_pct.loc[card] = 0.0
                
        return freq_pct.reindex(card_ids).rename(index=labels)
