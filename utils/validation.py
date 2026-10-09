from typing import List, Dict, Any, Tuple
import pandas as pd

def validate_study_meta(title: str, condition: str) -> Tuple[bool, str]:
    if not title or len(title.strip()) < 3:
        return False, "Study title must be at least 3 characters long."
    valid_conditions = ["OPEN", "CLOSED", "HYBRID", "PROPOSED"]
    if condition not in valid_conditions:
        return False, f"Invalid study condition. Must be one of {valid_conditions}"
    return True, ""

def validate_card_csv(df: pd.DataFrame) -> Tuple[bool, str, List[Dict[str, Any]]]:
    required_cols = {"title"}
    cols = {c.lower().strip() for c in df.columns}
    if not required_cols.issubset(cols):
        return False, "CSV file must contain at least a 'title' column.", []
    
    parsed_cards = []
    for idx, row in df.iterrows():
        title_val = str(row.get("title", "")).strip()
        if not title_val or title_val.lower() == "nan":
            continue
        parsed_cards.append({
            "title": title_val,
            "description": str(row.get("description", "")).strip() if "description" in row and pd.notna(row["description"]) else "",
            "example": str(row.get("example", "")).strip() if "example" in row and pd.notna(row["example"]) else "",
            "researcher_notes": str(row.get("notes", "")).strip() if "notes" in row and pd.notna(row["notes"]) else "",
        })
        
    if not parsed_cards:
        return False, "No valid cards found in the CSV file.", []
    return True, f"Successfully parsed {len(parsed_cards)} cards.", parsed_cards