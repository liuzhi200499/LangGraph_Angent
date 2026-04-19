# ChromaDB — 向量数据库技术文档

---

## 1. 技术概述

ChromaDB（简称 Chroma）是一个开源的轻量级向量数据库，专为 AI 应用设计。它内置文本向量化能力，支持语义搜索，无需额外部署向量计算服务，数据全部存储在本地文件系统中。

| 项目 | 说明 |
|------|------|
| 版本 | 1.5.8 |
| 语言 | Python |
| 官方文档 | https://docs.trychroma.com/ |
| 安装 | `pip install chromadb` |
| 数据存储 | 本地文件系统（PersistentClient） |
| 核心能力 | 自动向量化、语义搜索、元数据过滤、删除 |

---

## 2. 为什么选择 ChromaDB

| 特性 | ChromaDB | Pinecone | Milvus | FAISS |
|------|----------|----------|--------|-------|
| 部署方式 | 本地文件/服务 | 云服务 | 自建服务 | 本地库 |
| 内置嵌入 | 有 | 无 | 无 | 无 |
| 语义搜索 | 原生支持 | 原生支持 | 原生支持 | 需手动实现 |
| CRUD | 完整（增删查） | 完整 | 完整 | 仅查询 |
| 额外依赖 | 少量 | 账号+网络 | 重量级 | 无 |
| 适合场景 | 轻量原型/中小项目 | 生产云部署 | 大规模生产 | 高性能研究 |

本项目选择 ChromaDB 的原因：**零配置、纯本地、内置嵌入、支持删除**。

---

## 3. 安装与初始化

### 3.1 安装

```bash
pip install chromadb
# 当前最新版本：1.5.8（2026-04-16）
# 会自动安装 onnxruntime、tokenizers 等嵌入相关依赖
```

### 3.2 初始化数据库

```python
import chromadb

# 方式 1：持久化客户端（数据保存到磁盘，推荐生产使用）
client = chromadb.PersistentClient(path="./data/agent_memory")

# 方式 2：内存客户端（数据不持久化，适合测试）
# client = chromadb.Client()

print("ChromaDB 初始化完成")
```

### 3.3 数据目录结构

```
data/agent_memory/
├── chroma.sqlite3              # 元数据存储
└── {collection_id}/            # 每个集合的向量数据
    ├── data_level0.bin         # 向量索引文件
    └── metadata.bin            # 元数据文件
```

---

## 4. 核心使用流程

### 4.1 完整使用流程图

```
创建集合 → 插入数据（自动向量化） → 语义搜索 → 获取结果
   │            │                      │           │
   ▼            ▼                      ▼           ▼
 get_or_     collection.add()     collection.query()  返回相似度
 create_     自动对 documents      自动对查询文本       排序结果
 collection  做向量化             做向量化并匹配
```

### 4.2 第一步：创建集合（Collection）

```python
# 获取或创建集合（幂等操作，已存在则直接获取）
collection = client.get_or_create_collection(
    name="knowledge_chunks",
)

# 也可以单独创建（已存在会报错）
# collection = client.create_collection(name="knowledge_chunks")

# 查看已有集合
collections = client.list_collections()
```

**关键概念：**
- **Collection（集合）** = 类似数据库的"表"，存储文档及其向量
- ChromaDB 会自动对 `documents` 字段进行向量化，无需手动调用嵌入模型
- 默认使用 `all-MiniLM-L6-v2` 嵌入模型（首次使用自动下载）

### 4.3 第二步：插入数据

```python
collection = client.get_or_create_collection(name="knowledge_chunks")

# 批量插入（推荐）
collection.add(
    ids=["doc_001_0", "doc_001_1"],              # 唯一标识，必须提供
    documents=[                                    # 文本内容（自动向量化）
        "机器学习是人工智能的一个分支，它使计算机能够从数据中学习。",
        "深度学习是机器学习的一个子集，使用多层神经网络进行学习。"
    ],
    metadatas=[                                    # 元数据（可选，用于过滤）
        {"doc_id": "doc_001", "title": "机器学习入门", "chunk_index": 0},
        {"doc_id": "doc_001", "title": "深度学习概述", "chunk_index": 1},
    ]
)

# 单条插入
collection.add(
    ids=["doc_002_0"],
    documents=["Python 由 Guido van Rossum 于 1991 年创建。"],
    metadatas=[{"doc_id": "doc_002", "title": "Python 简介"}]
)
```

**关键规则：**
- `ids` 必须是唯一的，重复插入同一 id 会报错（如需更新用 `upsert`）
- `documents` 会被自动向量化并建立索引
- `metadatas` 是可选的键值对，支持后续按条件过滤和删除

### 4.4 第三步：语义搜索

```python
results = collection.query(
    query_texts=["什么是机器学习？"],     # 查询文本（自动向量化）
    n_results=5                          # 返回最相似的 5 条结果
)

# 解析结果
for i, doc in enumerate(results["documents"][0]):
    meta = results["metadatas"][0][i]
    distance = results["distances"][0][i]
    print(f"距离: {distance:.4f}")
    print(f"标题: {meta.get('title', '')}")
    print(f"内容: {doc[:100]}...")
    print("---")
```

**输出示例：**
```
距离: 0.3124
标题: 机器学习入门
内容: 机器学习是人工智能的一个分支，它使计算机能够从数据中学习。...
---
距离: 0.5891
标题: 深度学习概述
内容: 深度学习是机器学习的一个子集，使用多层神经网络进行学习。...
---
```

### 4.5 第四步：更新和删除

```python
# 更新记录（upsert：存在则更新，不存在则插入）
collection.upsert(
    ids=["doc_001_0"],
    documents=["机器学习是AI的核心分支，让计算机从数据中自动学习规律。"],
    metadatas=[{"doc_id": "doc_001", "title": "机器学习入门（修订版）"}]
)

# 按条件删除（通过元数据过滤）
collection.delete(where={"doc_id": "doc_001"})

# 按 ID 删除
collection.delete(ids=["doc_002_0"])

# 删除所有数据（清空集合）
collection.delete(where={})
```

---

## 5. 在项目中集成 ChromaDB

### 5.1 封装向量数据库管理器

```python
# db/vector_manager.py（与项目实际代码一致）
import os
from config.settings import settings


class VectorManager:
    """
    向量数据库管理器
    - 封装 ChromaDB 的初始化、数据写入和语义搜索操作
    - 延迟加载数据库实例，避免模块导入时的性能开销
    """

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or settings.VECTOR_DB_PATH
        self._client = None
        self._collections = {}

    def _get_client(self):
        """延迟加载 ChromaDB 客户端"""
        if self._client is None:
            import chromadb
            os.makedirs(self.persist_directory, exist_ok=True)
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        return self._client

    def _get_collection(self, table_name: str):
        """获取或创建集合（带缓存）"""
        if table_name not in self._collections:
            client = self._get_client()
            self._collections[table_name] = client.get_or_create_collection(
                name=table_name,
            )
        return self._collections[table_name]

    def init_table(self, table_name: str = "knowledge_chunks"):
        """初始化集合"""
        self._get_collection(table_name)

    def insert_records(self, table_name: str, records: list[dict]):
        """批量插入记录"""
        collection = self._get_collection(table_name)
        ids = [r["chunk_id"] for r in records]
        documents = [r["content"] for r in records]
        metadatas = [
            {"doc_id": r["doc_id"], "title": r["title"], "metadata": r.get("metadata", "")}
            for r in records
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, table_name: str, query_text: str, limit: int = None) -> list[dict]:
        """语义搜索"""
        limit = limit or settings.VECTOR_SEARCH_LIMIT
        collection = self._get_collection(table_name)
        results = collection.query(query_texts=[query_text], n_results=limit)

        records = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                records.append({
                    "title": meta.get("title", ""),
                    "content": doc,
                    "doc_id": meta.get("doc_id", ""),
                })
        return records

    def delete_by_doc_id(self, table_name: str, doc_id: str):
        """按文档 ID 删除所有分块"""
        collection = self._get_collection(table_name)
        collection.delete(where={"doc_id": doc_id})


vector_manager = VectorManager()
```

### 5.2 作为 LangGraph 工具使用

```python
from langchain_core.tools import tool
from db.vector_manager import vector_manager

@tool
def search_knowledge(query: str, top_k: int = 5) -> str:
    """在知识库中搜索与查询最相关的内容"""
    results = vector_manager.search("knowledge_chunks", query, top_k)

    if not results:
        return "知识库中未找到相关内容。"

    formatted = []
    for r in results:
        formatted.append(f"[{r.get('title', '未知')}] {r['content']}")

    return "\n\n---\n\n".join(formatted)
```

---

## 6. 文本分块策略

向量化前的文本分块质量直接影响搜索效果：

### 6.1 固定长度分块

```python
def fixed_chunk(text: str, chunk_size: int = 500) -> list[str]:
    """按固定字符数切分"""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
```

### 6.2 智能分块（推荐）

```python
def smart_chunk(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """在句子边界处切分，保留重叠"""
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for sep in ['。', '！', '？', '；', '\n', '.', '!', '?', ';']:
                pos = text.rfind(sep, start + chunk_size - overlap, end + overlap)
                if pos != -1:
                    end = pos + 1
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap

    return [c for c in chunks if c]
```

### 6.3 分块参数建议

| 参数 | 短文本（< 1万字符） | 中等文本（1-10万字符） | 长文本（> 10万字符） |
|------|---------------------|----------------------|---------------------|
| `chunk_size` | 300-500 | 500-800 | 800-1200 |
| `overlap` | 30-50 | 50-100 | 100-200 |

---

## 7. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 首次运行很慢 | 下载嵌入模型 | 等待下载完成（约 80MB），后续会缓存 |
| 搜索结果不相关 | 分块过大/过小 | 调整 `chunk_size` 为 500 左右 |
| 内存占用高 | 数据量过大 | 控制单集合记录数量，定期清理 |
| 中文搜索效果差 | 默认英文嵌入模型 | 创建集合时指定中文嵌入模型 |
| ids 重复报错 | 插入已有 id | 改用 `upsert` 或先 `delete` 再 `add` |

---

## 8. 备份与迁移

```bash
# 备份：直接复制数据目录
xcopy /E /I data\agent_memory backup\agent_memory_20260419

# 或使用 Python
python -c "import shutil; shutil.copytree('data/agent_memory', 'backup/agent_memory_20260419')"

# 恢复：将备份目录设为 path 参数
client = chromadb.PersistentClient(path="./backup/agent_memory_20260419")
```
