import uuid
import secrets
import io
import pandas as pd
from typing import List, Optional, Tuple
from database.models import Study, Card, Category
from database.repositories import StudyRepository, CardRepository, CategoryRepository
from utils.validation import validate_study_meta, validate_card_csv

class StudyService:
    def __init__(self, db_path: Optional[str] = None):
        self.study_repo = StudyRepository(db_path)
        self.card_repo = CardRepository(db_path)
        self.cat_repo = CategoryRepository(db_path)

    def create_study(
        self,
        title: str,
        description: str,
        instructions: str,
        researcher_info: str,
        condition: str,
        item_label: str = "Card",
        allow_new_categories: bool = True,
        allow_rename_categories: bool = True,
        allow_delete_categories: bool = True,
        allow_category_descriptions: bool = True,
        allow_unassigned: bool = True,
        require_all_placed: bool = True,
        log_interactions: bool = True,
        reflection_questions: Optional[List[str]] = None
    ) -> Tuple[bool, str, Optional[Study]]:
        is_valid, err = validate_study_meta(title, condition)
        if not is_valid:
            return False, err, None

        study_id = f"std_{uuid.uuid4().hex[:10]}"
        token = secrets.token_urlsafe(12)
        study = Study(
            study_id=study_id,
            token=token,
            title=title.strip(),
            description=description.strip(),
            instructions=instructions.strip(),
            researcher_info=researcher_info.strip(),
            condition=condition,
            item_label=item_label.strip() or "Card",
            allow_new_categories=allow_new_categories,
            allow_rename_categories=allow_rename_categories,
            allow_delete_categories=allow_delete_categories,
            allow_category_descriptions=allow_category_descriptions,
            allow_unassigned=allow_unassigned,
            require_all_placed=require_all_placed,
            log_interactions=log_interactions,
            reflection_questions=reflection_questions or ["Please explain your sorting logic."]
        )
        self.study_repo.save_study(study)
        return True, "Study created successfully.", study

    def update_study(self, study: Study) -> Tuple[bool, str]:
        is_valid, err = validate_study_meta(study.title, study.condition)
        if not is_valid:
            return False, err
        self.study_repo.save_study(study)
        return True, "Study updated successfully."

    def add_card_to_study(
        self, study_id: str, title: str, description: str = "", example: str = "", notes: str = "",
        fill: str = "#EFF6FF", text: str = "#0F172A", border: str = "#2563EB"
    ) -> Card:
        existing_cards = self.card_repo.get_cards_for_study(study_id, active_only=False)
        if title.strip().casefold() in {card.title.casefold() for card in existing_cards}:
            raise ValueError("Each card title must be unique within a study so the results remain reliable.")
        card = Card(
            card_id=f"crd_{uuid.uuid4().hex[:10]}",
            study_id=study_id,
            title=title.strip(),
            description=description.strip(),
            example=example.strip(),
            researcher_notes=notes.strip(),
            display_order=len(existing_cards) + 1,
            active=True, color_fill=fill, color_text=text, color_border=border
        )
        self.card_repo.save_cards([card])
        return card

    def import_cards_csv(self, study_id: str, csv_file_bytes: bytes) -> Tuple[bool, str]:
        valid, msg, card_dicts = validate_card_csv(csv_file_bytes)
        if not valid:
            return False, msg
        
        existing = self.card_repo.get_cards_for_study(study_id, active_only=False)
        existing_titles = {card.title.casefold() for card in existing}
        incoming_titles = [card["title"].casefold() for card in card_dicts]
        duplicate_titles = {title for title in incoming_titles if incoming_titles.count(title) > 1}
        if duplicate_titles:
            return False, "The uploaded CSV contains duplicate card titles. Give each card a unique title so results can be analyzed accurately."
        if existing_titles.intersection(incoming_titles):
            return False, "One or more CSV card titles already exist in this study. Card titles must be unique."
        start_order = len(existing) + 1
        cards_to_add = []
        for i, cd in enumerate(card_dicts):
            cards_to_add.append(Card(
                card_id=f"crd_{uuid.uuid4().hex[:10]}",
                study_id=study_id,
                title=cd["title"],
                description=cd["description"],
                example=cd["example"],
                researcher_notes=cd["researcher_notes"],
                display_order=start_order + i,
                active=True
            ))
        self.card_repo.save_cards(cards_to_add)
        return True, f"Successfully imported {len(cards_to_add)} cards."

    def export_cards_csv(self, study_id: str) -> str:
        cards = self.card_repo.get_cards_for_study(study_id, active_only=False)
        data = [c.to_dict() for c in cards]
        df = pd.DataFrame(data)
        return df.to_csv(index=False)

    def add_category_to_study(self, study_id: str, name: str, description: str = "", fill: str = "#FFFFFF", text: str = "#000000", border: str = "#CCCCCC") -> Category:
        existing = self.cat_repo.get_categories_for_study(study_id)
        cat = Category(
            category_id=f"cat_{uuid.uuid4().hex[:10]}",
            study_id=study_id,
            name=name.strip(),
            description=description.strip(),
            display_order=len(existing) + 1,
            color_fill=fill,
            color_text=text,
            color_border=border
        )
        self.cat_repo.save_categories([cat])
        return cat

    def get_study(self, study_id: str) -> Optional[Study]:
        return self.study_repo.get_study_by_id(study_id)

    def get_study_by_token(self, token: str) -> Optional[Study]:
        return self.study_repo.get_study_by_token(token)

    def get_all_studies(self) -> List[Study]:
        return self.study_repo.get_all_studies()

    def delete_study(self, study_id: str) -> None:
        self.study_repo.delete_study(study_id)
