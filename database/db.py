import os
import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
configured_db_path = Path(os.getenv("DATABASE_PATH", "card_sort.db")).expanduser()
# Keep the database with the project even when Streamlit is launched from a
# different working directory. An explicitly absolute DATABASE_PATH still wins.
DB_PATH = str(configured_db_path if configured_db_path.is_absolute() else PROJECT_ROOT / configured_db_path)

def get_connection(db_path=None):
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # SQLite does not enforce declared foreign keys unless every connection
    # explicitly enables them.  This makes study deletion clean up its related
    # cards, categories, and participant data as intended.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db(db_path=None):
    conn = get_connection(db_path)
    cursor = conn.cursor()
    
    # Studies table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS studies (
        study_id TEXT PRIMARY KEY,
        token TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        instructions TEXT,
        researcher_info TEXT,
        condition TEXT NOT NULL,
        item_label TEXT DEFAULT 'Card',
        allow_new_categories INTEGER DEFAULT 1,
        allow_rename_categories INTEGER DEFAULT 1,
        allow_delete_categories INTEGER DEFAULT 1,
        allow_category_descriptions INTEGER DEFAULT 1,
        allow_unassigned INTEGER DEFAULT 1,
        require_all_placed INTEGER DEFAULT 1,
        log_interactions INTEGER DEFAULT 1,
        reflection_questions_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # “Proposed” was an early label that is no longer offered. Existing data
    # is equivalent to a closed sort, so migrate it on startup.
    cursor.execute("UPDATE studies SET condition = 'CLOSED' WHERE condition = 'PROPOSED'")

    # Cards table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS cards (
        card_id TEXT PRIMARY KEY,
        study_id TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        example TEXT,
        researcher_notes TEXT,
        display_order INTEGER DEFAULT 0,
        active INTEGER DEFAULT 1,
        color_fill TEXT DEFAULT '#EFF6FF',
        color_text TEXT DEFAULT '#0F172A',
        color_border TEXT DEFAULT '#2563EB',
        FOREIGN KEY (study_id) REFERENCES studies (study_id) ON DELETE CASCADE
    )
    ''')

    # Lightweight migrations for databases created before card colors existed.
    # SQLite's CREATE TABLE IF NOT EXISTS does not add new columns to an
    # existing table, so check before altering it.
    card_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(cards)")}
    for name, default in {
        "color_fill": "'#EFF6FF'",
        "color_text": "'#0F172A'",
        "color_border": "'#2563EB'",
    }.items():
        if name not in card_columns:
            cursor.execute(f"ALTER TABLE cards ADD COLUMN {name} TEXT DEFAULT {default}")
    
    # Categories table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        category_id TEXT PRIMARY KEY,
        study_id TEXT NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        display_order INTEGER DEFAULT 0,
        color_fill TEXT DEFAULT '#FFFFFF',
        color_text TEXT DEFAULT '#000000',
        color_border TEXT DEFAULT '#CCCCCC',
        FOREIGN KEY (study_id) REFERENCES studies (study_id) ON DELETE CASCADE
    )
    ''')
    
    # Participant Sessions table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS participant_sessions (
        session_token TEXT PRIMARY KEY,
        study_id TEXT NOT NULL,
        status TEXT DEFAULT 'in_progress',
        completion_code TEXT UNIQUE,
        started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        completed_at TIMESTAMP,
        snapshot_json TEXT,
        FOREIGN KEY (study_id) REFERENCES studies (study_id) ON DELETE CASCADE
    )
    ''')
    
    # Card Placements table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS card_placements (
        placement_id TEXT PRIMARY KEY,
        session_token TEXT NOT NULL,
        card_id TEXT NOT NULL,
        category_name TEXT NOT NULL,
        card_order INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_token) REFERENCES participant_sessions (session_token) ON DELETE CASCADE,
        FOREIGN KEY (card_id) REFERENCES cards (card_id) ON DELETE CASCADE
    )
    ''')

    # Reflection Responses table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS reflection_responses (
        response_id TEXT PRIMARY KEY,
        session_token TEXT NOT NULL,
        question_index INTEGER NOT NULL,
        response_text TEXT,
        audio_file_path TEXT,
        FOREIGN KEY (session_token) REFERENCES participant_sessions (session_token) ON DELETE CASCADE
    )
    ''')
    
    # Interaction Events table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS interaction_events (
        event_id TEXT PRIMARY KEY,
        session_token TEXT NOT NULL,
        event_type TEXT NOT NULL,
        payload_json TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (session_token) REFERENCES participant_sessions (session_token) ON DELETE CASCADE
    )
    ''')

    conn.commit()
    conn.close()
