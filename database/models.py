from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class Study:
    study_id: str
    token: str
    title: str
    description: str = ""
    instructions: str = ""
    researcher_info: str = ""
    condition: str = "HYBRID"
    item_label: str = "Card"
    allow_new_categories: bool = True
    allow_rename_categories: bool = True
    allow_delete_categories: bool = True
    allow_category_descriptions: bool = True
    allow_unassigned: bool = True
    require_all_placed: bool = True
    log_interactions: bool = True
    reflection_questions: List[str] = field(default_factory=list)
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "study_id": self.study_id,
            "token": self.token,
            "title": self.title,
            "description": self.description,
            "instructions": self.instructions,
            "researcher_info": self.researcher_info,
            "condition": self.condition,
            "item_label": self.item_label,
            "allow_new_categories": self.allow_new_categories,
            "allow_rename_categories": self.allow_rename_categories,
            "allow_delete_categories": self.allow_delete_categories,
            "allow_category_descriptions": self.allow_category_descriptions,
            "allow_unassigned": self.allow_unassigned,
            "require_all_placed": self.require_all_placed,
            "log_interactions": self.log_interactions,
            "reflection_questions": self.reflection_questions,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

@dataclass
class Card:
    card_id: str
    study_id: str
    title: str
    description: str = ""
    example: str = ""
    researcher_notes: str = ""
    display_order: int = 0
    active: bool = True
    color_fill: str = "#EFF6FF"
    color_text: str = "#0F172A"
    color_border: str = "#2563EB"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "card_id": self.card_id,
            "study_id": self.study_id,
            "title": self.title,
            "description": self.description,
            "example": self.example,
            "researcher_notes": self.researcher_notes,
            "display_order": self.display_order,
            "active": self.active,
            "color_fill": self.color_fill,
            "color_text": self.color_text,
            "color_border": self.color_border,
        }

@dataclass
class Category:
    category_id: str
    study_id: str
    name: str
    description: str = ""
    display_order: int = 0
    color_fill: str = "#FFFFFF"
    color_text: str = "#000000"
    color_border: str = "#CCCCCC"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category_id": self.category_id,
            "study_id": self.study_id,
            "name": self.name,
            "description": self.description,
            "display_order": self.display_order,
            "color_fill": self.color_fill,
            "color_text": self.color_text,
            "color_border": self.color_border,
        }

@dataclass
class ParticipantSession:
    session_token: str
    study_id: str
    status: str = "in_progress"
    completion_code: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    snapshot_json: Optional[str] = None

@dataclass
class CardPlacement:
    placement_id: str
    session_token: str
    card_id: str
    category_name: str
    card_order: int = 0
    updated_at: Optional[str] = None

@dataclass
class ReflectionResponse:
    response_id: str
    session_token: str
    question_index: int
    response_text: str = ""
    audio_file_path: Optional[str] = None

@dataclass
class InteractionEvent:
    event_id: str
    session_token: str
    event_type: str
    payload_json: str = "{}"
    timestamp: Optional[str] = None
