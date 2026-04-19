"""
SQLite 数据库管理模块
负责管理对话记录、知识文档元数据和系统配置的持久化存储。
采用每次操作获取连接、用完即关的策略，避免多线程下的连接冲突。
"""
import sqlite3
import os
from typing import Optional
from config.settings import settings


class SQLiteManager:
    """
    SQLite 数据库管理器
    - 自动初始化数据库表结构（conversations / knowledge_documents / system_configs）
    - 提供对话消息、知识文档、系统配置的 CRUD 操作
    """

    def __init__(self, db_path: str = None):
        self.db_path = db_path or settings.SQLITE_DB_PATH
        # 确保数据库文件所在目录存在
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        # 初始化时创建所有必需的表
        self._init_tables()

    def _get_conn(self) -> sqlite3.Connection:
        """获取数据库连接，启用 Row 工厂以支持字典式访问"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        """初始化所有数据库表，使用 IF NOT EXISTS 确保幂等"""
        conn = self._get_conn()
        conn.executescript("""
            -- 对话记录表：存储所有用户与 AI 的对话消息
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                thread_id TEXT NOT NULL,          -- 会话线程ID，用于区分不同对话
                user_id TEXT DEFAULT 'default',   -- 用户标识
                role TEXT NOT NULL,               -- 消息角色：user / assistant / system
                content TEXT NOT NULL,            -- 消息内容
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            -- 为高频查询字段创建索引，提升查询性能
            CREATE INDEX IF NOT EXISTS idx_conversations_thread_id ON conversations(thread_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

            -- 知识文档表：存储导入文档的元数据信息
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT UNIQUE NOT NULL,       -- 文档唯一标识
                title TEXT,                        -- 文档标题
                source TEXT,                       -- 来源（manual / wiki / file 等）
                file_type TEXT DEFAULT 'text',     -- 文件类型
                chunk_count INTEGER DEFAULT 0,     -- 文档被切分成的块数
                status TEXT DEFAULT 'active',      -- 状态：active / deleted（软删除）
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            -- 系统配置表：存储可动态修改的键值对配置
            CREATE TABLE IF NOT EXISTS system_configs (
                key TEXT PRIMARY KEY,              -- 配置键
                value TEXT,                        -- 配置值
                description TEXT,                  -- 配置说明
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()

    # ==================== 对话消息操作 ====================

    def save_message(self, thread_id: str, user_id: str, role: str, content: str):
        """保存一条对话消息到数据库"""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO conversations (thread_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (thread_id, user_id, role, content),
        )
        conn.commit()
        conn.close()

    def load_messages(self, thread_id: str, limit: int = None) -> list[dict]:
        """加载指定会话的最近 N 条消息，按时间正序返回"""
        limit = limit or settings.MAX_HISTORY_MESSAGES
        conn = self._get_conn()
        # 先按 id 降序取最近的消息，再反转为时间正序
        rows = conn.execute(
            "SELECT role, content, created_at FROM conversations WHERE thread_id = ? ORDER BY id DESC LIMIT ?",
            (thread_id, limit),
        ).fetchall()
        conn.close()
        return [dict(r) for r in reversed(rows)]

    def get_conversation_threads(self, user_id: str = "default") -> list[dict]:
        """获取指定用户的所有会话线程列表，按最近活跃时间排序"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT DISTINCT thread_id, user_id, MAX(created_at) as last_active FROM conversations WHERE user_id = ? GROUP BY thread_id ORDER BY last_active DESC",
            (user_id,),
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    # ==================== 知识文档操作 ====================

    def save_document_meta(self, doc_id: str, title: str, source: str, chunk_count: int):
        """保存知识文档的元数据信息"""
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO knowledge_documents (doc_id, title, source, chunk_count) VALUES (?, ?, ?, ?)",
            (doc_id, title, source, chunk_count),
        )
        conn.commit()
        conn.close()

    def get_document_meta(self, doc_id: str) -> Optional[dict]:
        """根据文档 ID 查询文档元数据"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM knowledge_documents WHERE doc_id = ?", (doc_id,)
        ).fetchone()
        conn.close()
        return dict(row) if row else None

    def list_documents(self) -> list[dict]:
        """获取所有活跃状态的文档列表"""
        conn = self._get_conn()
        rows = conn.execute(
            "SELECT * FROM knowledge_documents WHERE status = 'active' ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def delete_document(self, doc_id: str):
        """软删除文档，仅更新状态为 deleted，不实际移除数据"""
        conn = self._get_conn()
        conn.execute(
            "UPDATE knowledge_documents SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE doc_id = ?",
            (doc_id,),
        )
        conn.commit()
        conn.close()

    def get_knowledge_stats(self) -> dict:
        """获取知识库统计数据：活跃文档数和总分块数"""
        conn = self._get_conn()
        doc_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge_documents WHERE status = 'active'"
        ).fetchone()[0]
        total_chunks = conn.execute(
            "SELECT COALESCE(SUM(chunk_count), 0) FROM knowledge_documents WHERE status = 'active'"
        ).fetchone()[0]
        conn.close()
        return {"document_count": doc_count, "total_chunks": total_chunks}

    # ==================== 系统配置操作 ====================

    def set_config(self, key: str, value: str, description: str = ""):
        """设置或更新一个系统配置项（键值对）"""
        conn = self._get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO system_configs (key, value, description, updated_at) VALUES (?, ?, ?, CURRENT_TIMESTAMP)",
            (key, value, description),
        )
        conn.commit()
        conn.close()

    def get_config(self, key: str) -> Optional[str]:
        """根据键名获取配置值"""
        conn = self._get_conn()
        row = conn.execute(
            "SELECT value FROM system_configs WHERE key = ?", (key,)
        ).fetchone()
        conn.close()
        return row["value"] if row else None


# 全局单例，供其他模块直接导入使用
sqlite_manager = SQLiteManager()
