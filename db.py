import sqlite3
from datetime import date, timedelta

import config

# Інтервали повторення (у днях) для кожної "коробки" — спрощений алгоритм Лейтнера
INTERVALS = [0, 1, 3, 7, 14, 30, 60]
LEARNED_BOX = 4

USER_FIELDS = {"name", "level", "scenario", "correction", "voice_reply", "reminders"}

_conn: sqlite3.Connection | None = None


def conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def init():
    c = conn()
    c.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            level TEXT DEFAULT 'A2',
            scenario TEXT,
            correction TEXT DEFAULT 'all',
            voice_reply INTEGER DEFAULT 0,
            reminders INTEGER DEFAULT 1,
            xp INTEGER DEFAULT 0,
            streak INTEGER DEFAULT 0,
            last_active TEXT,
            messages INTEGER DEFAULT 0,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            content TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id);
        CREATE TABLE IF NOT EXISTS words (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            word TEXT,
            translation TEXT,
            transcription TEXT,
            example TEXT,
            example_uk TEXT,
            box INTEGER DEFAULT 0,
            next_review TEXT,
            created TEXT DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_words_user ON words(user_id);
        CREATE TABLE IF NOT EXISTS groups (
            id INTEGER PRIMARY KEY,
            title TEXT
        );
        """
    )
    c.commit()


def _today() -> str:
    return date.today().isoformat()


# ---------- users ----------

def get_user(uid: int) -> dict | None:
    row = conn().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()
    return dict(row) if row else None


def create_user(uid: int, name: str) -> dict:
    conn().execute("INSERT OR IGNORE INTO users (id, name) VALUES (?, ?)", (uid, name))
    conn().commit()
    return get_user(uid)


def ensure_user(uid: int, name: str) -> dict:
    return get_user(uid) or create_user(uid, name)


def update_user(uid: int, **fields):
    fields = {k: v for k, v in fields.items() if k in USER_FIELDS}
    if not fields:
        return
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn().execute(f"UPDATE users SET {sets} WHERE id = ?", (*fields.values(), uid))
    conn().commit()


def register_activity(uid: int, xp: int = 0, chat_message: bool = False):
    """Нараховує XP і оновлює стрік (кількість днів поспіль)."""
    user = get_user(uid)
    if not user:
        return
    today = date.today()
    last = user["last_active"]
    streak = user["streak"]
    if last != today.isoformat():
        streak = streak + 1 if last == (today - timedelta(days=1)).isoformat() else 1
    conn().execute(
        "UPDATE users SET xp = xp + ?, streak = ?, last_active = ?, messages = messages + ? WHERE id = ?",
        (xp, streak, today.isoformat(), 1 if chat_message else 0, uid),
    )
    conn().commit()


def users_with_reminders() -> list[dict]:
    rows = conn().execute("SELECT * FROM users WHERE reminders = 1").fetchall()
    return [dict(r) for r in rows]


# ---------- history ----------

def add_history(uid: int, role: str, content: str):
    c = conn()
    c.execute("INSERT INTO history (user_id, role, content) VALUES (?, ?, ?)", (uid, role, content))
    c.execute(
        "DELETE FROM history WHERE user_id = ? AND id NOT IN "
        "(SELECT id FROM history WHERE user_id = ? ORDER BY id DESC LIMIT 40)",
        (uid, uid),
    )
    c.commit()


def get_history(uid: int, limit: int = 16) -> list[dict]:
    rows = conn().execute(
        "SELECT role, content FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?", (uid, limit)
    ).fetchall()
    return [{"role": r["role"], "content": r["content"]} for r in reversed(rows)]


def clear_history(uid: int):
    conn().execute("DELETE FROM history WHERE user_id = ?", (uid,))
    conn().commit()


# ---------- words ----------

def word_exists(uid: int, word: str) -> bool:
    row = conn().execute(
        "SELECT 1 FROM words WHERE user_id = ? AND lower(word) = lower(?)", (uid, word.strip())
    ).fetchone()
    return row is not None


def add_word(uid: int, word: str, translation: str, transcription: str = "",
             example: str = "", example_uk: str = "") -> int:
    cur = conn().execute(
        "INSERT INTO words (user_id, word, translation, transcription, example, example_uk, next_review) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (uid, word.strip(), translation, transcription, example, example_uk, _today()),
    )
    conn().commit()
    return cur.lastrowid


def get_word(uid: int, word_id: int) -> dict | None:
    row = conn().execute("SELECT * FROM words WHERE id = ? AND user_id = ?", (word_id, uid)).fetchone()
    return dict(row) if row else None


def list_words(uid: int, offset: int = 0, limit: int = 15) -> list[dict]:
    rows = conn().execute(
        "SELECT * FROM words WHERE user_id = ? ORDER BY id DESC LIMIT ? OFFSET ?", (uid, limit, offset)
    ).fetchall()
    return [dict(r) for r in rows]


def count_words(uid: int) -> int:
    return conn().execute("SELECT COUNT(*) FROM words WHERE user_id = ?", (uid,)).fetchone()[0]


def count_learned(uid: int) -> int:
    return conn().execute(
        "SELECT COUNT(*) FROM words WHERE user_id = ? AND box >= ?", (uid, LEARNED_BOX)
    ).fetchone()[0]


def count_due(uid: int) -> int:
    return conn().execute(
        "SELECT COUNT(*) FROM words WHERE user_id = ? AND next_review <= ?", (uid, _today())
    ).fetchone()[0]


def delete_word_by_text(uid: int, word: str) -> bool:
    cur = conn().execute("DELETE FROM words WHERE user_id = ? AND lower(word) = lower(?)", (uid, word.strip()))
    conn().commit()
    return cur.rowcount > 0


def due_word(uid: int) -> dict | None:
    row = conn().execute(
        "SELECT * FROM words WHERE user_id = ? AND next_review <= ? ORDER BY box, RANDOM() LIMIT 1",
        (uid, _today()),
    ).fetchone()
    return dict(row) if row else None


def random_words(uid: int, n: int) -> list[dict]:
    rows = conn().execute(
        "SELECT * FROM words WHERE user_id = ? ORDER BY RANDOM() LIMIT ?", (uid, n)
    ).fetchall()
    return [dict(r) for r in rows]


def review_word(uid: int, word_id: int, correct: bool):
    w = get_word(uid, word_id)
    if not w:
        return
    box = min(w["box"] + 1, len(INTERVALS) - 1) if correct else 0
    next_review = (date.today() + timedelta(days=INTERVALS[box])).isoformat()
    conn().execute("UPDATE words SET box = ?, next_review = ? WHERE id = ?", (box, next_review, word_id))
    conn().commit()


# ---------- groups ----------

def save_group(chat_id: int, title: str):
    conn().execute("INSERT OR REPLACE INTO groups (id, title) VALUES (?, ?)", (chat_id, title))
    conn().commit()


def all_groups() -> list[int]:
    return [r[0] for r in conn().execute("SELECT id FROM groups").fetchall()]


def remove_group(chat_id: int):
    conn().execute("DELETE FROM groups WHERE id = ?", (chat_id,))
    conn().commit()
