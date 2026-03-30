import sqlite3
from datetime import datetime

DB_PATH = "job_bot.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS sources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL UNIQUE,
            ats_type TEXT,
            category TEXT,
            active INTEGER DEFAULT 1,
            added_date TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Add category column if upgrading from older DB
    try:
        c.execute("ALTER TABLE sources ADD COLUMN category TEXT")
        conn.commit()
    except Exception:
        pass

    c.execute("""
        CREATE TABLE IF NOT EXISTS preferences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS seen_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id INTEGER,
            job_id TEXT NOT NULL,
            title TEXT,
            company TEXT,
            url TEXT,
            found_date TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(source_id, job_id)
        )
    """)

    conn.commit()
    conn.close()


# --- Sources ---

def add_source(name, url, ats_type=None, category=None):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO sources (name, url, ats_type, category) VALUES (?, ?, ?, ?)",
            (name, url, ats_type, category)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()


def remove_source(name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM sources WHERE LOWER(name) = LOWER(?)", (name,))
    affected = c.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def list_sources():
    conn = get_connection()
    rows = conn.execute("SELECT * FROM sources WHERE active = 1 ORDER BY name").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_source_by_id(source_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM sources WHERE id = ?", (source_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Preferences ---

def set_preference(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO preferences (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )
    conn.commit()
    conn.close()


def get_preference(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM preferences WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def get_all_preferences():
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM preferences").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


# --- Seen jobs ---

def is_job_seen(source_id, job_id):
    conn = get_connection()
    row = conn.execute(
        "SELECT id FROM seen_jobs WHERE source_id = ? AND job_id = ?",
        (source_id, job_id)
    ).fetchone()
    conn.close()
    return row is not None


def mark_job_seen(source_id, job_id, title, company, url):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO seen_jobs (source_id, job_id, title, company, url) VALUES (?, ?, ?, ?, ?)",
            (source_id, job_id, title, company, url)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
