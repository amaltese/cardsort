import io
from typing import List, Dict, Any, Tuple
import pandas as pd

TITLE_ALIASES = {'title', 'card', 'cards', 'item', 'items', 'name', 'capacity', 'concept', 'skill', 'strategy', 'idea', 'behavior', 'attribute', 'header'}
DESC_ALIASES = {'description', 'desc', 'details', 'detail', 'info', 'text', 'definition'}
EXAMPLE_ALIASES = {'example', 'examples', 'sample'}
NOTES_ALIASES = {'notes', 'researcher_notes', 'internal_notes', 'comment', 'comments'}

def validate_study_meta(title: str, condition: str) -> Tuple[bool, str]:
    if not title or len(title.strip()) < 3:
        return False, "Study title must be at least 3 characters long."
    valid_conditions = ["OPEN", "CLOSED", "HYBRID"]
    if condition not in valid_conditions:
        return False, f"Invalid study condition. Must be one of {valid_conditions}"
    return True, ""

def validate_card_csv(csv_input: Any) -> Tuple[bool, str, List[Dict[str, Any]]]:
    if csv_input is None:
        return False, "No CSV file uploaded.", []

    # Handle DataFrame vs Bytes vs String inputs cleanly
    if isinstance(csv_input, pd.DataFrame):
        df = csv_input
    elif isinstance(csv_input, (bytes, bytearray)):
        if len(csv_input) == 0:
            return False, "The uploaded file is empty.", []
        text = None
        for encoding in ['utf-8-sig', 'utf-8', 'latin1', 'cp1252']:
            try:
                text = csv_input.decode(encoding)
                break
            except Exception:
                continue
        if not text:
            return False, "Unable to read file encoding. Please save CSV as UTF-8.", []

        try:
            # Parse the uploaded CSV exactly as supplied.  In particular, do
            # not strip surrounding quotes line-by-line: quoted commas and
            # multi-line descriptions are valid CSV and pandas handles them.
            df = pd.read_csv(io.StringIO(text), sep=None, engine='python', dtype=str, keep_default_na=False)
        except Exception:
            try:
                df = pd.read_csv(io.StringIO(text), dtype=str, keep_default_na=False)
            except Exception as e:
                return False, f"Failed to parse CSV file: {str(e)}", []

        # A few spreadsheet exports wrap the entire CSV in one quoted field.
        # Only unwrap that narrow case after a normal parse has produced one
        # column whose header itself contains commas.
        if len(df.columns) == 1 and "," in str(df.columns[0]):
            wrapped = text.strip()
            if wrapped.startswith('"') and wrapped.endswith('"'):
                try:
                    df = pd.read_csv(
                        io.StringIO(wrapped[1:-1].replace('""', '"')),
                        sep=None, engine='python', dtype=str, keep_default_na=False,
                    )
                except Exception:
                    pass
    elif isinstance(csv_input, str):
        if not csv_input.strip():
            return False, "The provided CSV text is empty.", []
        try:
            df = pd.read_csv(io.StringIO(csv_input))
        except Exception as e:
            return False, f"Failed to parse CSV text: {str(e)}", []
    else:
        return False, "Invalid CSV input format.", []

    if df.empty:
        return False, "The CSV file contains no data rows.", []

    # Flexible column header mapping
    col_map = {}
    for col in df.columns:
        normalized = str(col).strip().strip('"').strip("'").lower().replace(" ", "_")
        if normalized in TITLE_ALIASES and 'title' not in col_map:
            col_map['title'] = col
        elif normalized in DESC_ALIASES and 'description' not in col_map:
            col_map['description'] = col
        elif normalized in EXAMPLE_ALIASES and 'example' not in col_map:
            col_map['example'] = col
        elif normalized in NOTES_ALIASES and 'notes' not in col_map:
            col_map['notes'] = col

    # Fallback: Use column 0 if no header matches
    if 'title' not in col_map:
        first_col = df.columns[0]
        col_map['title'] = first_col

    title_col = col_map['title']
    desc_col = col_map.get('description')
    example_col = col_map.get('example')
    notes_col = col_map.get('notes')

    parsed_cards = []
    for idx, row in df.iterrows():
        title_val = str(row[title_col]).strip() if pd.notna(row[title_col]) else ""
        if not title_val or title_val.lower() == 'nan':
            continue

        desc_val = str(row[desc_col]).strip() if desc_col and pd.notna(row[desc_col]) else ""
        example_val = str(row[example_col]).strip() if example_col and pd.notna(row[example_col]) else ""
        notes_val = str(row[notes_col]).strip() if notes_col and pd.notna(row[notes_col]) else ""

        if desc_val.lower() == 'nan': desc_val = ""
        if example_val.lower() == 'nan': example_val = ""
        if notes_val.lower() == 'nan': notes_val = ""

        parsed_cards.append({
            'title': title_val,
            'description': desc_val,
            'example': example_val,
            'researcher_notes': notes_val,
        })

    if not parsed_cards:
        return False, "No valid items found in the uploaded file.", []

    return True, f"Successfully parsed {len(parsed_cards)} items.", parsed_cards
