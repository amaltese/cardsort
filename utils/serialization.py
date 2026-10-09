import json
from typing import Dict, Any, List
from database.models import Study, Card, Category

def serialize_study_snapshot(study: Study, cards: List[Card], categories: List[Category]) -> str:
    snapshot = {
        "study": study.to_dict(),
        "cards": [c.to_dict() for c in cards],
        "categories": [cat.to_dict() for cat in categories]
    }
    return json.dumps(snapshot, indent=2)

def deserialize_study_snapshot(snapshot_json: str) -> Dict[str, Any]:
    return json.loads(snapshot_json)