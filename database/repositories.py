import json
import sqlite3
from typing import List, Optional
from database.db import get_connection
from database.models import Study, Card, Category, ParticipantSession, CardPlacement

class StudyRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def save_study(self, study: Study) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO studies (
            study_id, token, title, description, instructions, researcher_info,
            condition, item_label, allow_new_categories, allow_rename_categories,
            allow_delete_categories, allow_category_descriptions, allow_unassigned,
            require_all_placed, log_interactions, reflection_questions_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(study_id) DO UPDATE SET
            title=excluded.title, description=excluded.description,
            instructions=excluded.instructions, researcher_info=excluded.researcher_info,
            condition=excluded.condition, item_label=excluded.item_label,
            allow_new_categories=excluded.allow_new_categories,
            allow_rename_categories=excluded.allow_rename_categories,
            allow_delete_categories=excluded.allow_delete_categories,
            allow_category_descriptions=excluded.allow_category_descriptions,
            allow_unassigned=excluded.allow_unassigned,
            require_all_placed=excluded.require_all_placed,
            log_interactions=excluded.log_interactions,
            reflection_questions_json=excluded.reflection_questions_json,
            updated_at=CURRENT_TIMESTAMP
        """, (
            study.study_id, study.token, study.title, study.description,
            study.instructions, study.researcher_info, study.condition,
            study.item_label, int(study.allow_new_categories), int(study.allow_rename_categories),
            int(study.allow_delete_categories), int(study.allow_category_descriptions),
            int(study.allow_unassigned), int(study.require_all_placed),
            int(study.log_interactions), json.dumps(study.reflection_questions)
        ))
        conn.commit()
        conn.close()

    def get_study_by_id(self, study_id: str) -> Optional[Study]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies WHERE study_id = ?", (study_id,))
        row = cursor.fetchone()
        conn.close()
        return self._map_study(row) if row else None

    def get_study_by_token(self, token: str) -> Optional[Study]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies WHERE token = ?", (token,))
        row = cursor.fetchone()
        conn.close()
        return self._map_study(row) if row else None

    def get_all_studies(self) -> List[Study]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM studies ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [self._map_study(row) for row in rows]

    def _map_study(self, row: sqlite3.Row) -> Study:
        return Study(
            study_id=row["study_id"],
            token=row["token"],
            title=row["title"],
            description=row["description"] or "",
            instructions=row["instructions"] or "",
            researcher_info=row["researcher_info"] or "",
            condition=row["condition"],
            item_label=row["item_label"] or "Card",
            allow_new_categories=bool(row["allow_new_categories"]),
            allow_rename_categories=bool(row["allow_rename_categories"]),
            allow_delete_categories=bool(row["allow_delete_categories"]),
            allow_category_descriptions=bool(row["allow_category_descriptions"]),
            allow_unassigned=bool(row["allow_unassigned"]),
            require_all_placed=bool(row["require_all_placed"]),
            log_interactions=bool(row["log_interactions"]),
            reflection_questions=json.loads(row["reflection_questions_json"] or "[]"),
            created_at=str(row["created_at"]),
            updated_at=str(row["updated_at"])
        )

class CardRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def save_cards(self, cards: List[Card]) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        for card in cards:
            cursor.execute("""
            INSERT INTO cards (card_id, study_id, title, description, example, researcher_notes, display_order, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(card_id) DO UPDATE SET
                title=excluded.title, description=excluded.description,
                example=excluded.example, researcher_notes=excluded.researcher_notes,
                display_order=excluded.display_order, active=excluded.active
            """, (card.card_id, card.study_id, card.title, card.description, card.example, card.researcher_notes, card.display_order, int(card.active)))
        conn.commit()
        conn.close()

    def delete_card(self, card_id: str) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cards WHERE card_id = ?", (card_id,))
        conn.commit()
        conn.close()

    def get_cards_for_study(self, study_id: str, active_only: bool = True) -> List[Card]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        if active_only:
            cursor.execute("SELECT * FROM cards WHERE study_id = ? AND active = 1 ORDER BY display_order ASC", (study_id,))
        else:
            cursor.execute("SELECT * FROM cards WHERE study_id = ? ORDER BY display_order ASC", (study_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Card(
            card_id=r["card_id"], study_id=r["study_id"], title=r["title"],
            description=r["description"] or "", example=r["example"] or "",
            researcher_notes=r["researcher_notes"] or "", display_order=r["display_order"],
            active=bool(r["active"])
        ) for r in rows]

class CategoryRepository:
    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path

    def save_categories(self, categories: List[Category]) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        for cat in categories:
            cursor.execute("""
            INSERT INTO categories (category_id, study_id, name, description, display_order, color_fill, color_text, color_border)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(category_id) DO UPDATE SET
                name=excluded.name, description=excluded.description,
                display_order=excluded.display_order, color_fill=excluded.color_fill,
                color_text=excluded.color_text, color_border=excluded.color_border
            """, (cat.category_id, cat.study_id, cat.name, cat.description, cat.display_order, cat.color_fill, cat.color_text, cat.color_border))
        conn.commit()
        conn.close()

    def delete_category(self, category_id: str) -> None:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM categories WHERE category_id = ?", (category_id,))
        conn.commit()
        conn.close()

    def get_categories_for_study(self, study_id: str) -> List[Category]:
        conn = get_connection(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM categories WHERE study_id = ? ORDER BY display_order ASC", (study_id,))
        rows = cursor.fetchall()
        conn.close()
        return [Category(
            category_id=r["category_id"], study_id=r["study_id"], name=r["name"],
            description=r["description"] or "", display_order=r["display_order"],
            color_fill=r["color_fill"] or "#FFFFFF", color_text=r["color_text"] or "#000000",
            color_border=r["color_border"] or "#CCCCCC"
        ) for r in rows]