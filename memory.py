"""
Persistent memory using SQLite with FTS5 full-text search.
"""

import sqlite3
import re


class Memory:
    def __init__(self, db_path: str = "jarvis_memory.db"):
        self.db_path = db_path
        self._init_db()
        count = self._count()
        print(f"[Memory] Loaded {count} memories from {db_path}")

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL, value TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
            USING fts5(key, value, content=memories, content_rowid=id)
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_insert AFTER INSERT ON memories BEGIN
                INSERT INTO memories_fts(rowid, key, value) VALUES (new.id, new.key, new.value);
            END
        """)
        c.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_delete AFTER DELETE ON memories BEGIN
                INSERT INTO memories_fts(memories_fts, rowid, key, value)
                VALUES ('delete', old.id, old.key, old.value);
            END
        """)
        conn.commit()
        conn.close()

    def _count(self) -> int:
        conn = sqlite3.connect(self.db_path)
        count = conn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
        conn.close()
        return count

    def remember(self, key: str, value: str):
        conn = sqlite3.connect(self.db_path)
        existing = conn.execute("SELECT id FROM memories WHERE key = ?", (key,)).fetchone()
        if existing:
            conn.execute("DELETE FROM memories WHERE id = ?", (existing[0],))
        conn.execute("INSERT INTO memories (key, value) VALUES (?, ?)", (key, value))
        conn.commit()
        conn.close()
        print(f"[Memory] Stored: {key} = {value}")

    def recall(self, query: str, limit: int = 5) -> list[dict]:
        conn = sqlite3.connect(self.db_path)
        try:
            results = conn.execute("""
                SELECT m.key, m.value, m.created_at
                FROM memories_fts fts JOIN memories m ON fts.rowid = m.id
                WHERE memories_fts MATCH ? ORDER BY rank LIMIT ?
            """, (query, limit)).fetchall()
        except sqlite3.OperationalError:
            results = conn.execute("""
                SELECT key, value, created_at FROM memories
                WHERE key LIKE ? OR value LIKE ?
                ORDER BY created_at DESC LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit)).fetchall()
        finally:
            conn.close()
        return [{"key": r[0], "value": r[1], "created_at": r[2]} for r in results]


def extract_memories(text: str) -> tuple[str, list[tuple[str, str]]]:
    pattern = r'\[REMEMBER\s+(.+?)=(.+?)\]'
    memories = [(m.group(1).strip(), m.group(2).strip()) for m in re.finditer(pattern, text)]
    clean_text = re.sub(pattern, '', text).strip()
    return clean_text, memories
