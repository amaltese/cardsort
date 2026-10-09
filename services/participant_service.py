import secrets
from typing import Optional, Dict, Any
from database.models import ParticipantSession, Study
from database.repositories import StudyRepository
from database.db import get_connection

class ParticipantService:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path
        self.study_repo = StudyRepository(db_path)

    def initialize_session(self, study_token: str) -> Optional[Dict[str, Any]]:
        study = self.study_repo.get_study_by_token(study_token)
        if not study:
            return None

        session_token = f"sess_{secrets.token_urlsafe(16)}"
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO participant_sessions (session_token, study_id, status)
        VALUES (?, ?, 'in_progress')
        """, (session_token, study.study_id))
        conn.commit()
        conn.close()

        return {
            "session_token": session_token,
            "study": study
        }