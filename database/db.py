import os
import sqlite3
from pathlib import Path
from typing import Dict, List

from services.google_storage import is_configured, load_state, save_state

PROJECT_ROOT = Path(__file__).resolve().parent.parent
configured_db_path = Path(os.getenv("DATABASE_PATH", "card_sort.db")).expanduser()
# Keep the database with the project even when Streamlit is launched from a
# different working directory. An explicitly absolute DATABASE_PATH still wins.
DB_PATH = str(configured_db_path if configured_db_path.is_absolute() else PROJECT_ROOT / configured_db_path)

SYNC_TABLES = [
    "studies", "cards", "categories", "participant_sessions",
    "card_placements", "reflection_responses", "interaction_events",
]
_remote_state_loaded = False
_sync_suspended = False


def _is_primary_database(connection: sqlite3.Connection) -> bool:
    """Do not send temporary test databases or alternate paths to Google."""
    try:
        database_file = next(row[2] for row in connection.execute("PRAGMA database_list") if row[1] == "main")
        return Path(database_file).resolve() == Path(DB_PATH).resolve()
    except (OSError, StopIteration):
        return False


def _export_state(connection: sqlite3.Connection) -> Dict[str, List[Dict[str, object]]]:
    tables: Dict[str, List[Dict[str, object]]] = {}
    for name in SYNC_TABLES:
        rows = connection.execute(f"SELECT * FROM {name}").fetchall()
        tables[name] = [dict(row) for row in rows]
    return {"tables": tables}


def _restore_state(connection: sqlite3.Connection, state: Dict[str, object]) -> None:
    """Replace a blank local runtime database with its private Sheet snapshot."""
    global _sync_suspended
    tables = state.get("tables", {}) if isinstance(state, dict) else {}
    if not any(tables.get(name) for name in SYNC_TABLES):
        return

    _sync_suspended = True
    try:
        for name in reversed(SYNC_TABLES):
            connection.execute(f"DELETE FROM {name}")
        for name in SYNC_TABLES:
            rows = tables.get(name, [])
            if not rows:
                continue
            columns = list(rows[0].keys())
            column_list = ", ".join(columns)
            placeholders = ", ".join("?" for _ in columns)
            values = [tuple(row.get(column) for column in columns) for row in rows]
            connection.executemany(f"INSERT INTO {name} ({column_list}) VALUES ({placeholders})", values)
        sqlite3.Connection.commit(connection)
    finally:
        _sync_suspended = False


class SyncedConnection(sqlite3.Connection):
    """Normal local SQLite connection used by the app during an interaction."""

    def commit(self):
        sqlite3.Connection.commit(self)


def sync_database(db_path=None) -> None:
    """Persist the complete local state at deliberate, meaningful save points.

    Syncing every card movement made the participant experience wait for a
    network round trip.  Interaction events remain local until the completed
    sort is saved, while study edits and submissions call this function.
    """
    if db_path or not _remote_state_loaded or not is_configured():
        return
    conn = get_connection()
    try:
        if _is_primary_database(conn):
            save_state(_export_state(conn))
    finally:
        conn.close()

def get_connection(db_path=None):
    target_path = db_path or DB_PATH
    conn = sqlite3.connect(target_path, check_same_thread=False, factory=SyncedConnection)
    conn.row_factory = sqlite3.Row
    # SQLite does not enforce declared foreign keys unless every connection
    # explicitly enables them.  This makes study deletion clean up its related
    # cards, categories, and participant data as intended.
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn

def init_db(db_path=None):
    global _remote_state_loaded
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
        category_order TEXT DEFAULT 'RANDOM',
        reflection_questions_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    # “Proposed” was an early label that is no longer offered. Existing data
    # is equivalent to a closed sort, so migrate it on startup.
    cursor.execute("UPDATE studies SET condition = 'CLOSED' WHERE condition = 'PROPOSED'")
    study_columns = {row["name"] for row in cursor.execute("PRAGMA table_info(studies)")}
    if "category_order" not in study_columns:
        cursor.execute("ALTER TABLE studies ADD COLUMN category_order TEXT DEFAULT 'RANDOM'")

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

    # Do not mirror schema creation before an existing remote snapshot is
    # restored.  Otherwise a fresh Community Cloud container could overwrite
    # the researcher's saved data with empty tables.
    sqlite3.Connection.commit(conn)

    if not db_path and not _remote_state_loaded and is_configured():
        try:
            _restore_state(conn, load_state() or {})
        finally:
            # A temporary network failure should not repeatedly download state
            # during a single page render. A later app restart will retry.
            _remote_state_loaded = True
    elif not db_path:
        _remote_state_loaded = True
    conn.close()
