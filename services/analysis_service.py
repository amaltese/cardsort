import json
import pandas as pd
from typing import List, Dict, Any, Optional
from database.db import get_connection

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

    def get_co_occurrence_matrix(self, study_id: str, card_titles: List[str]) -> pd.DataFrame:
        snapshots = self.get_completed_snapshots(study_id)
        if not card_titles:
            return pd.DataFrame()
            
        co_matrix = pd.DataFrame(0.0, index=card_titles, columns=card_titles)
        n_participants = len(snapshots)
        
        if n_participants == 0:
            return co_matrix

        for snap in snapshots:
            placements = snap.get("placements", {})
            for cat_name, items in placements.items():
                valid_cards = [c for c in items if c in card_titles]
                for i in range(len(valid_cards)):
                    for j in range(len(valid_cards)):
                        co_matrix.loc[valid_cards[i], valid_cards[j]] += 1.0

        co_matrix = (co_matrix / n_participants) * 100.0
        return co_matrix.round(1)

    def get_card_agreement_summary(self, study_id: str, card_titles: List[str]) -> pd.DataFrame:
        snapshots = self.get_completed_snapshots(study_id)
        n_participants = len(snapshots)
        
        if n_participants == 0 or not card_titles:
            return pd.DataFrame(columns=["Card Title", "Primary Category", "Agreement %", "Agreement Level"])

        cat_rows = []
        for snap in snapshots:
            placements = snap.get("placements", {})
            for cat_name, items in placements.items():
                for card in items:
                    if card in card_titles:
                        cat_rows.append({"card": card, "category": cat_name})

        if not cat_rows:
            return pd.DataFrame(columns=["Card Title", "Primary Category", "Agreement %", "Agreement Level"])

        df_cat = pd.DataFrame(cat_rows)
        freq_matrix = pd.crosstab(df_cat["card"], df_cat["category"])

        summary = []
        for card in card_titles:
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
                    "Card Title": card,
                    "Primary Category": top_cat,
                    "Agreement %": pct,
                    "Agreement Level": level
                })
            else:
                summary.append({
                    "Card Title": card,
                    "Primary Category": "Unassigned",
                    "Agreement %": 0.0,
                    "Agreement Level": "🔴 Unsorted"
                })

        return pd.DataFrame(summary)

    def get_card_category_frequency(self, study_id: str, card_titles: List[str]) -> pd.DataFrame:
        snapshots = self.get_completed_snapshots(study_id)
        n_participants = len(snapshots)
        
        if n_participants == 0 or not card_titles:
            return pd.DataFrame()

        cat_rows = []
        for snap in snapshots:
            placements = snap.get("placements", {})
            for cat_name, items in placements.items():
                for card in items:
                    if card in card_titles:
                        cat_rows.append({"card": card, "category": cat_name})

        if not cat_rows:
            return pd.DataFrame()

        df_cat = pd.DataFrame(cat_rows)
        freq_matrix = pd.crosstab(df_cat["card"], df_cat["category"])
        freq_pct = (freq_matrix.div(n_participants, axis=0) * 100).round(1)
        
        # Ensure all study cards are present in index
        for card in card_titles:
            if card not in freq_pct.index:
                freq_pct.loc[card] = 0.0
                
        return freq_pct.reindex(card_titles)
