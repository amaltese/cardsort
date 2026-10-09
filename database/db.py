import os
import sqlite3

DB_PATH = os.getenv("DATABASE_PATH", "card_sort.db")

def get_connection(db_path=None):
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
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
        FOREIGN KEY (study_id) REFERENCES studies (study_id) ON DELETE CASCADE
    )
    ''')
    
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
