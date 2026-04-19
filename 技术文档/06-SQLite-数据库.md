# SQLite — 数据库技术文档

---

## 1. 技术概述

SQLite 是一个轻量级的嵌入式关系数据库，整个数据库存储在单个文件中，无需独立的服务进程。本项目用它存储对话记录、知识文档元数据和系统配置。

**为什么需要数据库？** 在 AI Agent 应用中，有好几类数据需要持久化存储：用户和 Agent 的对话历史（下次打开还能看到之前的聊天）、上传的知识文档信息（记录哪些文档已被导入、包含多少分块）、系统配置（如默认模型、温度参数等设置）。SQLite 就像一个轻便的"记事本"，应用运行时把数据写进去，下次启动时还能读出来。

本项目选择 SQLite 而不是 MySQL/PostgreSQL 的原因很简单：不需要安装额外的数据库服务，Python 内置支持，数据就是一个文件，备份和迁移非常方便。对于单机部署的 Agent 应用来说完全够用。

| 项目 | 说明 |
|------|------|
| 版本 | Python 内置（sqlite3 模块） |
| 安装 | 无需安装，Python 标准库 |
| 数据存储 | 单个 `.db` 文件 |
| 适用场景 | 本地应用、原型开发、中小规模数据 |

---

## 2. 为什么选择 SQLite

对于本项目来说，SQLite 和 MySQL/PostgreSQL 最大的区别在于：SQLite 不需要安装和启动一个独立的数据库服务，整个数据库就是一个文件。这意味着部署时少一个依赖，维护时少一个服务要管。当然，SQLite 也有局限性——它不支持高并发写入（多个进程同时写会锁库），但对于本项目的单用户场景来说完全不是问题。

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

使用 SQLite 的第一步是建立数据库连接。如果指定的数据库文件不存在，SQLite 会自动创建一个新的空数据库文件。操作完成后记得关闭连接，否则会占用系统资源。

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

直接用 `connect()` 和 `close()` 管理连接容易忘记关闭，导致资源泄漏。推荐使用 Python 的 `closing()` 上下文管理器来确保连接一定会被关闭。另外，`sqlite3` 的 `with` 语句管理的是事务（自动提交或回滚），而不是连接的关闭，所以需要配合 `closing()` 一起使用。设置 `row_factory = sqlite3.Row` 可以让查询结果返回字典风格的对象，通过列名访问数据比通过索引更直观。

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

本项目定义了三张核心表来管理不同类型的数据。`conversations` 表存储用户和 Agent 的对话记录，每条消息记录属于哪个会话（thread_id）、谁说的（role）以及内容；`knowledge_documents` 表记录上传的知识文档元信息，包括文档标题、来源和分块数量；`system_configs` 表采用键值对方式存储系统配置，方便动态修改设置而不用改代码。下面的代码展示了完整的建表过程：

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

CRUD 是数据库操作的四个基本动作：Create（创建）、Read（读取）、Update（更新）、Delete（删除）。这四个操作覆盖了绝大多数数据管理需求。下面对每张表展示完整的 CRUD 操作示例。

### 5.1 插入数据（Create）

插入数据使用 SQL 的 `INSERT INTO` 语句。注意所有值都通过 `?` 占位符传入，这是防止 SQL 注入的标准做法——永远不要用字符串拼接来构造 SQL 语句。

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

查询使用 `SELECT` 语句。查询对话历史时，我们按时间倒序取最新的 N 条记录，然后再翻转成正序（最早的在前面），这样用户看到的就是自然的时间线顺序。`LIMIT` 参数控制每次加载的消息数量，避免一次性加载过多数据。

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

更新使用 `UPDATE` 语句。`system_configs` 表的 `set_config` 函数使用了 SQLite 的 `ON CONFLICT ... DO UPDATE` 语法（即"UPSERT"），如果 key 已存在就更新，不存在就插入，非常方便。这比先查询再决定插入还是更新要高效得多。

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

删除有两种策略：物理删除（`DELETE` 语句直接移除记录）和逻辑删除（将 `status` 字段设为 `deleted`，记录仍保留在数据库中）。本项目对文档采用逻辑删除，这样可以防止误删，也方便审计数据变更历史。对对话记录则使用物理删除，因为用户明确要求清空对话时应该彻底删除。

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

为了简化数据库操作，我们将常用的数据库操作封装成一个 `SQLiteManager` 类。这个类在初始化时自动创建数据目录和所有必要的表，使用时只需调用封装好的方法（如 `save_message`、`load_messages`），不需要手写 SQL 语句。内部使用了 `PRAGMA journal_mode=WAL` 模式，这是 SQLite 的一种高效日志模式，允许在读操作的同时进行写操作，提高了并发性能。

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

SQLite 的备份非常简单——因为整个数据库就是一个文件，复制文件就等于备份。但直接复制可能在写入过程中导致备份文件损坏，所以推荐使用 SQLite 内置的 `.backup` 命令，它会在确保数据一致性的前提下进行备份。`VACUUM` 命令用于清理数据库碎片、回收空间，在大量删除操作后执行可以减小文件大小并提升查询性能。

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

使用 SQLite 时最常见的问题是 `database is locked`，这通常发生在多个进程同时尝试写入同一个数据库文件时。解决方案是开启 WAL 模式（Write-Ahead Logging），它允许多个读者和一个写者同时操作数据库，大大减少了锁冲突的概率。

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `database is locked` | 多进程同时写入 | 使用 WAL 模式：`PRAGMA journal_mode=WAL` |
| 数据库文件过大 | 大量未清理数据 | 定期 VACUUM 和清理旧记录 |
| 查询慢 | 缺少索引 | 为常用查询字段创建索引 |
| 编码问题 | 中文乱码 | 确保连接使用 UTF-8 |
