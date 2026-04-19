# SQLite — 数据库技术文档

---

## 1. 技术概述

SQLite 是一个轻量级的嵌入式关系数据库，整个数据库存储在单个文件中，无需独立的服务进程。本项目用它存储对话记录、知识文档元数据和系统配置。

| 项目 | 说明 |
|------|------|
| 版本 | Python 内置（sqlite3 模块） |
| 安装 | 无需安装，Python 标准库 |
| 数据存储 | 单个 `.db` 文件 |
| 适用场景 | 本地应用、原型开发、中小规模数据 |

---

## 2. 为什么选择 SQLite

| 特性 | SQLite | MySQL/PostgreSQL |
|------|--------|------------------|
| 安装 | 无需安装 | 需要安装服务 |
| 运行方式 | 嵌入应用 | 独立进程 |
| 配置 | 零配置 | 需配置连接 |
| 数据存储 | 单文件 | 多文件/目录 |
| 并发 | 读并发，写串行 | 完整并发 |
| 备份 | 复制文件 | 导出/工具 |

**本项目选择 SQLite 的理由：** 轻量本地部署，无需额外服务，数据单文件管理。

---

## 3. 基础使用

### 3.1 连接数据库

```python
import sqlite3

# 连接数据库（文件不存在则自动创建）
conn = sqlite3.connect("data/agent.db")

# 创建游标
cursor = conn.cursor()

# 使用完毕后关闭
conn.close()
```

### 3.2 使用上下文管理器（推荐）

```python
import sqlite3
from contextlib import closing

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect("data/agent.db")
    conn.row_factory = sqlite3.Row  # 返回字典风格结果
    return conn

# 注意：sqlite3 的 with 只管理事务（提交/回滚），不关闭连接
# 需配合 closing() 确保连接被正确关闭
with closing(get_connection()) as conn:
    with conn:  # 管理事务
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM conversations")
        rows = cursor.fetchall()
```

---

## 4. 建表操作

### 4.1 本项目的三张核心表

```python
import sqlite3

def init_database(db_path="data/agent.db"):
    """初始化数据库表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 对话记录表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            thread_id TEXT NOT NULL,
            user_id TEXT DEFAULT 'default',
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # 创建索引（加速查询）
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_thread_id
        ON conversations(thread_id)
    """)
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_conversations_user_id
        ON conversations(user_id)
    """)

    # 知识文档元数据表
    cursor.execute("""
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
        )
    """)

    # 系统配置表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS system_configs (
            key TEXT PRIMARY KEY,
            value TEXT,
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()
    print("数据库初始化完成")
```

---

## 5. CRUD 操作

### 5.1 插入数据（Create）

```python
def save_message(thread_id: str, user_id: str, role: str, content: str):
    """保存一条对话消息"""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO conversations (thread_id, user_id, role, content) VALUES (?, ?, ?, ?)",
            (thread_id, user_id, role, content)
        )

def save_document_meta(doc_id: str, title: str, source: str, chunk_count: int):
    """保存知识文档元数据"""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO knowledge_documents
               (doc_id, title, source, chunk_count) VALUES (?, ?, ?, ?)""",
            (doc_id, title, source, chunk_count)
        )
```

**安全提示：** 始终使用参数化查询（`?` 占位符），不要用字符串拼接，防止 SQL 注入。

### 5.2 查询数据（Read）

```python
def load_messages(thread_id: str, limit: int = 20) -> list[dict]:
    """加载指定会话的对话历史"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT role, content, created_at FROM conversations
               WHERE thread_id = ? ORDER BY created_at DESC LIMIT ?""",
            (thread_id, limit)
        ).fetchall()
        return [dict(row) for row in reversed(rows)]  # 按时间正序返回

def get_document(doc_id: str) -> dict:
    """获取文档元数据"""
    with get_connection() as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM knowledge_documents WHERE doc_id = ?",
            (doc_id,)
        ).fetchone()
        return dict(row) if row else None

def get_config(key: str, default: str = None) -> str:
    """获取系统配置"""
    with get_connection() as conn:
        row = conn.execute(
            "SELECT value FROM system_configs WHERE key = ?",
            (key,)
        ).fetchone()
        return row[0] if row else default
```

### 5.3 更新数据（Update）

```python
def update_document_status(doc_id: str, status: str):
    """更新文档状态"""
    with get_connection() as conn:
        conn.execute(
            """UPDATE knowledge_documents
               SET status = ?, updated_at = CURRENT_TIMESTAMP
               WHERE doc_id = ?""",
            (status, doc_id)
        )

def set_config(key: str, value: str, description: str = ""):
    """设置系统配置（存在则更新，不存在则插入）"""
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO system_configs (key, value, description)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE SET
               value = excluded.value,
               description = excluded.description,
               updated_at = CURRENT_TIMESTAMP""",
            (key, value, description)
        )
```

### 5.4 删除数据（Delete）

```python
def delete_document(doc_id: str):
    """删除文档"""
    with get_connection() as conn:
        conn.execute(
            "UPDATE knowledge_documents SET status = 'deleted' WHERE doc_id = ?",
            (doc_id,)
        )
        # 或物理删除
        # conn.execute("DELETE FROM knowledge_documents WHERE doc_id = ?", (doc_id,))

def clear_conversation(thread_id: str):
    """清空指定会话"""
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM conversations WHERE thread_id = ?",
            (thread_id,)
        )
```

---

## 6. 封装数据库管理器

```python
# db/sqlite_manager.py
import sqlite3
from pathlib import Path

class SQLiteManager:
    def __init__(self, db_path: str = "data/agent.db"):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_tables()

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # 提高并发性能
        return conn

    def _init_tables(self):
        with self._get_conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    thread_id TEXT NOT NULL,
                    user_id TEXT DEFAULT 'default',
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_conv_thread ON conversations(thread_id);

                CREATE TABLE IF NOT EXISTS knowledge_documents (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    doc_id TEXT UNIQUE NOT NULL,
                    title TEXT, source TEXT,
                    file_type TEXT DEFAULT 'text',
                    chunk_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS system_configs (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    description TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

    def save_message(self, thread_id, user_id, role, content):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO conversations (thread_id, user_id, role, content) VALUES (?,?,?,?)",
                (thread_id, user_id, role, content)
            )

    def load_messages(self, thread_id, limit=20):
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT role, content FROM conversations WHERE thread_id=? ORDER BY id DESC LIMIT ?",
                (thread_id, limit)
            ).fetchall()
            return list(reversed([dict(r) for r in rows]))

    def save_document(self, doc_id, title, source, chunk_count):
        with self._get_conn() as conn:
            conn.execute(
                "INSERT INTO knowledge_documents (doc_id, title, source, chunk_count) VALUES (?,?,?,?)",
                (doc_id, title, source, chunk_count)
            )

    def get_stats(self):
        with self._get_conn() as conn:
            docs = conn.execute("SELECT COUNT(*) FROM knowledge_documents WHERE status='active'").fetchone()[0]
            msgs = conn.execute("SELECT COUNT(DISTINCT thread_id) FROM conversations").fetchone()[0]
            return {"documents": docs, "sessions": msgs}
```

---

## 7. 备份与维护

```bash
# 备份（安全方式，不会锁库）
sqlite3 data/agent.db ".backup 'backup/agent_20260419.db'"

# 压缩备份
gzip backup/agent_20260419.db

# 查看数据库大小
ls -lh data/agent.db

# 优化数据库（清理碎片）
sqlite3 data/agent.db "VACUUM;"
```

---

## 8. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `database is locked` | 多进程同时写入 | 使用 WAL 模式：`PRAGMA journal_mode=WAL` |
| 数据库文件过大 | 大量未清理数据 | 定期 VACUUM 和清理旧记录 |
| 查询慢 | 缺少索引 | 为常用查询字段创建索引 |
| 编码问题 | 中文乱码 | 确保连接使用 UTF-8 |
