import sqlite3
import os
from typing import Optional
from config.settings import settings


class SQLiteManager:
    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,
                user_id TEXT DEFAULT 'default',
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_conversations_thread_id ON conversations(thread_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,
                title TEXT,
                source TEXT,
                file_type TEXT DEFAULT 'text',
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS system_configs (
                key TEXT PRIMARY KEY,
                value TEXT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    def save_message(self, thread_id: str, user_id: str, role: str, content: str):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO conversations (thread_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (thread_id, user_id, role, content),
        )
        conn.commit()
        conn.close()

    def load_messages(self, thread_id: str, limit: int = None) -> list[dict]:
        limit = limit or settings.MAX_HISTORY_MESSAGES
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversations WHERE thread_id = ? ORDER BY id DESC LIMIT ?",
            (thread_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    def get_conversation_threads(self, user_id: str = "default") -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT thread_id, user_id, MAX(created_at) as last_active FROM conversations WHERE user_id = ? GROUP BY thread_id ORDER BY last_active DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def save_document_meta(self, doc_id: str, title: str, source: str, chunk_count: int):
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO knowledge_documents (doc_id, title, source, chunk_count) VALUES (?, ?, ?, ?)",
            (doc_id, title, source, chunk_count),
        )
        conn.commit()
        conn.close()

    def get_document_meta(self, doc_id: str) -> Optional[dict]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM knowledge_documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_documents(self) -> list[dict]:
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM knowledge_documents WHERE status = 'active' ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str):
        conn = self._get_conn()
        conn.execute(
            "UPDATE knowledge_documents SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE doc_id = ?",
            (doc_id,),
        )
        conn.commit()
        conn.close()

    def get_knowledge_stats(self) -> dict:
        conn = self._get_conn()
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge_documents WHERE status = 'active'"
        ).fetchone()[0]
        total_chunks = conn.execute(
            "SELECT COALESCE(SUM(chunk_count), 0) FROM knowledge_documents WHERE status = 'active'"
        ).fetchone()[0]
        conn.close()
        return {"document_count": doc_count, "total_chunks": total_chunks}

    def set_config(self, key: str, value: str, description: str = ""):
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO system_configs (key, value, description, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (key, value, description),
        )
        conn.commit()
        conn.close()

    def get_config(self, key: str) -> Optional[str]:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM system_configs WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row["value"] if row else None


sqlite_manager = SQLiteManager()
