import json
import pandas as pd
from typing import List, Dict, Any, Optional
from database.db import get_connection

class ExportService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def get_completed_sessions_for_study(self, study_id: str) -> List[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        SELECT session_token, status, completion_code, started_at, completed_at, snapshot_json
        FROM participant_sessions
        WHERE study_id = ? AND status = 'completed'
        ORDER BY completed_at DESC
        """, (study_id,))
        rows = cursor.fetchall()
        conn.close()

        results = []
        for r in rows:
            snap = json.loads(r["snapshot_json"]) if r["snapshot_json"] else {}
            results.append({
                "session_token": r["session_token"],
                "completion_code": r["completion_code"] or "N/A",
                "started_at": str(r["started_at"]) if r["started_at"] else "",
                "completed_at": str(r["completed_at"]) if r["completed_at"] else "",
                "placements": snap.get("placements", {}),
                "reflection": snap.get("reflection", "")
            })
        return results

    def export_results_csv(self, study_id: str) -> str:
        sessions = self.get_completed_sessions_for_study(study_id)
        rows = []
        for s in sessions:
            code = s["completion_code"]
            completed_at = s["completed_at"]
            reflection = s["reflection"]
            placements = s["placements"]
            for cat_name, items in placements.items():
                for item_title in items:
                    rows.append({
                        "completion_code": code,
                        "completed_at": completed_at,
                        "category_name": cat_name,
                        "card_title": item_title,
                        "participant_reflection": reflection
                    })
        if not rows:
            df = pd.DataFrame(columns=["completion_code", "completed_at", "category_name", "card_title", "participant_reflection"])
        else:
            df = pd.DataFrame(rows)
        return df.to_csv(index=False)
