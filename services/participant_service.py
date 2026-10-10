import json
import uuid
import secrets
from typing import Optional, Dict, Any, List
from database.models import ParticipantSession, Study, Card
from database.repositories import StudyRepository, CategoryRepository
from database.db import get_connection

class ParticipantService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.study_repo = StudyRepository(db_path)
        self.cat_repo = CategoryRepository(db_path)

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

    def record_interaction(self, session_token: str, study: Study, event_type: str, payload: Dict[str, Any]) -> None:
        """Store participant actions only when the study explicitly enables it."""
        if not study.log_interactions:
            return
        conn = get_connection(self.db_path)
        try:
            conn.execute(
                """INSERT INTO interaction_events (event_id, session_token, event_type, payload_json)
                   VALUES (?, ?, ?, ?)""",
                (f"evt_{uuid.uuid4().hex[:12]}", session_token, event_type, json.dumps(payload)),
            )
            conn.commit()
        finally:
            conn.close()

    def _validate_submission(
        self, session_token: str, study: Study, cards: List[Card], placements: Dict[str, List[str]]
    ) -> None:
        session = self.get_session(session_token)
        if not session or session["study_id"] != study.study_id:
            raise ValueError("This session does not belong to the current study. Please start the study again.")
        if session["status"] == "completed":
            raise ValueError("This submission has already been completed.")

        valid_ids = {card.card_id for card in cards}
        submitted_ids = [card_id for card_ids in placements.values() for card_id in card_ids]
        if any(card_id not in valid_ids for card_id in submitted_ids):
            raise ValueError("The submitted cards do not match this study. Please refresh and try again.")
        if len(submitted_ids) != len(set(submitted_ids)):
            raise ValueError("A card was placed more than once. Please refresh and try again.")
        if set(submitted_ids) != valid_ids:
            raise ValueError("Every current card must appear exactly once before the sort can be submitted.")

        unassigned = placements.get("Unassigned", [])
        if unassigned and (study.require_all_placed or not study.allow_unassigned):
            raise ValueError("All cards must be assigned to a category before submitting this study.")

        if study.condition == "CLOSED":
            allowed_categories = {
                category.name for category in self.cat_repo.get_categories_for_study(study.study_id)
            }
            unexpected = set(placements) - allowed_categories - {"Unassigned"}
            if unexpected:
                raise ValueError("This study uses predefined categories; new categories cannot be submitted.")

    def submit_sort(
        self,
        session_token: str,
        study: Study,
        cards: List[Card],
        placements: Dict[str, List[str]],
        reflection_responses: Optional[List[Dict[str, str]]] = None,
        category_descriptions: Optional[Dict[str, str]] = None,
    ) -> str:
        self._validate_submission(session_token, study, cards, placements)
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
            "placement_card_ids": placements,
            "category_descriptions": category_descriptions or {},
            "reflections": reflection_responses or [],
            # Kept for older exports and studies with one reflection question.
            "reflection": "\n\n".join(
                response.get("response", "").strip()
                for response in (reflection_responses or [])
                if response.get("response", "").strip()
            ),
        }
        snapshot_json = json.dumps(snapshot_data, indent=2)

        conn = get_connection(self.db_path)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM card_placements WHERE session_token = ?", (session_token,))
        cursor.execute("DELETE FROM reflection_responses WHERE session_token = ?", (session_token,))

        for cat_name, card_ids in placements.items():
            for order, cid in enumerate(card_ids):
                placement_id = f"plc_{uuid.uuid4().hex[:10]}"
                cursor.execute("""
                INSERT INTO card_placements (placement_id, session_token, card_id, category_name, card_order)
                VALUES (?, ?, ?, ?, ?)
                """, (placement_id, session_token, cid, cat_name, order))

        for question_index, response in enumerate(reflection_responses or []):
            response_text = response.get("response", "").strip()
            if response_text:
                cursor.execute(
                    """INSERT INTO reflection_responses (response_id, session_token, question_index, response_text)
                       VALUES (?, ?, ?, ?)""",
                    (f"rfl_{uuid.uuid4().hex[:12]}", session_token, question_index, response_text),
                )

        cursor.execute("""
        UPDATE participant_sessions
        SET status = 'completed',
            completion_code = ?,
            completed_at = CURRENT_TIMESTAMP,
            snapshot_json = ?
        WHERE session_token = ?
        """, (completion_code, snapshot_json, session_token))

        if study.log_interactions:
            cursor.execute(
                """INSERT INTO interaction_events (event_id, session_token, event_type, payload_json)
                   VALUES (?, ?, ?, ?)""",
                (f"evt_{uuid.uuid4().hex[:12]}", session_token, "sort_submitted", json.dumps({"card_count": len(cards)})),
            )

        conn.commit()
        conn.close()
        return completion_code
