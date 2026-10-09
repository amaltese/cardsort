import json
import uuid
import secrets
from typing import Optional, Dict, Any, List
from database.models import ParticipantSession, Study, Card
from database.repositories import StudyRepository
from database.db import get_connection

class ParticipantService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.study_repo = StudyRepository(db_path)

    def generate_completion_code(self) -> str:
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        return f"{part1}-{part2}"

    def create_fresh_session(self, study_id: str) -> Dict[str, Any]:
        new_token = f"sess_{secrets.token_urlsafe(16)}"
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO participant_sessions (session_token, study_id, status)
        VALUES (?, ?, 'in_progress')
        """, (new_token, study_id))
        conn.commit()
        
        cursor.execute("SELECT * FROM participant_sessions WHERE session_token = ?", (new_token,))
        row = cursor.fetchone()
        conn.close()
        return dict(row)

    def get_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM participant_sessions WHERE session_token = ?", (session_token,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None

    def submit_sort(
        self,
        session_token: str,
        study: Study,
        cards: List[Card],
        placements: Dict[str, List[str]],
        reflection_text: str = ""
    ) -> str:
        completion_code = self.generate_completion_code()
        cards_by_id = {c.card_id: c.title for c in cards}

        final_summary = {}
        for cat_name, card_ids in placements.items():
            if cat_name == "Unassigned" and not card_ids:
                continue
            final_summary[cat_name] = [cards_by_id.get(cid, cid) for cid in card_ids]

        snapshot_data = {
            "study_id": study.study_id,
            "study_title": study.title,
            "condition": study.condition,
            "placements": final_summary,
            "reflection": reflection_text.strip()
        }
        snapshot_json = json.dumps(snapshot_data, indent=2)

        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM card_placements WHERE session_token = ?", (session_token,))

        for cat_name, card_ids in placements.items():
            for order, cid in enumerate(card_ids):
                placement_id = f"plc_{uuid.uuid4().hex[:10]}"
                cursor.execute("""
                INSERT INTO card_placements (placement_id, session_token, card_id, category_name, card_order)
                VALUES (?, ?, ?, ?, ?)
                """, (placement_id, session_token, cid, cat_name, order))

        cursor.execute("""
        UPDATE participant_sessions
        SET status = 'completed',
            completion_code = ?,
            completed_at = CURRENT_TIMESTAMP,
            snapshot_json = ?
        WHERE session_token = ?
        """, (completion_code, snapshot_json, session_token))

        conn.commit()
        conn.close()
        return completion_code
