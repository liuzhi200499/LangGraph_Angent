# ChromaDB — 向量数据库技术文档

---

## 1. 技术概述

ChromaDB（简称 Chroma）是一个开源的轻量级向量数据库，专为 AI 应用设计。它内置文本向量化能力，支持语义搜索，无需额外部署向量计算服务，数据全部存储在本地文件系统中。

**什么是向量数据库？** 简单来说，传统数据库（如 SQLite）通过"精确匹配"来搜索——你搜"机器学习"，它只返回包含"机器学习"这四个字的记录。而向量数据库通过"语义相似度"来搜索——你搜"机器学习"，它也能找到包含"人工智能"、"深度学习"、"神经网络"等内容的记录，因为这些概念在语义上是相近的。它的工作原理是：先把文本转换成数学向量（一串数字），然后通过计算向量之间的距离来判断两段文本的语义相似度。

本项目使用 ChromaDB 来存储知识文档的向量索引，让 Agent 能够根据用户的提问，快速找到最相关的知识内容。

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

市面上的向量数据库有很多选择，下表对比了几个主流方案的差异。选择 ChromaDB 的核心原因是：本项目是轻量级本地应用，不需要复杂的分布式部署，ChromaDB 的"零配置、纯本地"特性正好满足需求，而且它支持自定义嵌入模型，对中文搜索效果更好。

| 特性 | ChromaDB | Pinecone | Milvus | FAISS |
|------|----------|----------|--------|-------|
| 部署方式 | 本地文件/服务 | 云服务 | 自建服务 | 本地库 |
| 内置嵌入 | 有 | 无 | 无 | 无 |
| 语义搜索 | 原生支持 | 原生支持 | 原生支持 | 需手动实现 |
| CRUD | 完整（增删查） | 完整 | 完整 | 仅查询 |
| 自定义嵌入 | 支持 | 支持 | 支持 | 需手动 |
| 额外依赖 | 少量 | 账号+网络 | 重量级 | 无 |
| 适合场景 | 轻量原型/中小项目 | 生产云部署 | 大规模生产 | 高性能研究 |

本项目选择 ChromaDB 的原因：**零配置、纯本地、支持自定义嵌入模型、支持删除**。

---

## 3. 安装与初始化

### 3.1 安装

```bash
pip install chromadb
# 当前最新版本：1.5.8（2026-04-16）
# 会自动安装 onnxruntime、tokenizers 等嵌入相关依赖
```

### 3.2 初始化数据库

ChromaDB 提供两种运行模式：持久化模式把数据保存到磁盘，重启程序后数据还在；内存模式数据只存在于运行期间，程序关闭就丢失。生产环境推荐使用持久化模式。初始化时只需指定一个目录路径，ChromaDB 会自动创建所需的文件结构。

```python
import chromadb

# 方式 1：持久化客户端（数据保存到磁盘，推荐生产使用）
client = chromadb.PersistentClient(path="./data/agent_memory")

# 方式 2：内存客户端（数据不持久化，适合测试）
# client = chromadb.Client()

print("ChromaDB 初始化完成")
```

### 3.3 数据目录结构

了解数据目录结构有助于备份和调试。ChromaDB 把元数据存储在一个 SQLite 文件中，而向量数据按集合分开存储在各自的子目录里。每个集合目录下包含向量索引文件和元数据文件。整体结构如下：

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

集合（Collection）是 ChromaDB 中存储数据的基本单元，类似于关系数据库中的"表"。每个集合包含一组文档及其对应的向量。推荐使用 `get_or_create_collection` 方法，它是幂等操作——集合不存在就创建，已存在就获取，不会报错。

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
- ChromaDB 支持自定义嵌入函数，本项目使用 `BAAI/bge-small-zh-v1.5` 中文嵌入模型
- 如果不指定嵌入函数，默认使用 `all-MiniLM-L6-v2`（英文为主，中文效果较差）

### 4.3 第二步：插入数据

向集合中插入数据时，你需要提供三个要素：唯一 ID、文本内容（documents）和可选的元数据（metadatas）。ChromaDB 会自动将文本内容转换为向量并建立索引，你不需要手动处理向量化过程。元数据是键值对形式的附加信息，比如文档标题、来源等，后续可以用来过滤搜索结果。

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

语义搜索是向量数据库最核心的功能。你传入一段查询文本，ChromaDB 会自动将其向量化，然后在集合中找到与之语义最相似的文档。`n_results` 参数控制返回的结果数量。返回结果中最重要的指标是 `distance`（距离），值越小表示越相似，通常 0.5 以下的相关性就比较高了。

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

数据不会永远不变，你需要能够更新和删除已有记录。`upsert` 方法是"更新或插入"的组合：如果 id 已存在就更新内容，不存在就插入新记录。删除操作可以通过 id 精确删除，也可以通过元数据条件批量删除（比如删除某个文档的所有分块）。

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

为了在项目中方便使用 ChromaDB，我们将其封装为 `VectorManager` 类。这个类采用"延迟加载"模式——只有在第一次实际使用时才初始化 ChromaDB 客户端和嵌入模型，避免在程序启动时就加载大量依赖，加快启动速度。同时内置了集合缓存，避免重复创建相同的集合实例。

下面是与项目实际代码完全一致的实现，包含初始化、插入、搜索、删除四个核心操作：

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
        self._embedding_fn = None
        self._collections = {}

    def _get_client(self):
        """延迟加载 ChromaDB 客户端和嵌入函数"""
        if self._client is None:
            import chromadb
            from chromadb.utils import embedding_functions
            os.makedirs(self.persist_directory, exist_ok=True)
            # 使用中文嵌入模型，比默认英文模型效果更好
            self._embedding_fn = embedding_functions.HuggingFaceEmbeddingFunction(
                model_name="BAAI/bge-small-zh-v1.5",
            )
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        return self._client

    def _get_collection(self, table_name: str):
        """获取或创建集合（带缓存，绑定嵌入函数）"""
        if table_name not in self._collections:
            client = self._get_client()
            self._collections[table_name] = client.get_or_create_collection(
                name=table_name,
                embedding_function=self._embedding_fn,
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

在 LangGraph Agent 中，向量搜索需要被包装成一个"工具"（Tool），这样 Agent 才能在对话过程中自主决定何时调用知识库搜索。使用 LangChain 的 `@tool` 装饰器，只需要定义一个函数并添加描述，Agent 就能理解这个工具的用途并正确使用它。函数的 docstring 会作为工具描述传递给 LLM，帮助模型判断何时应该调用此工具。

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

在将文档存入向量数据库之前，需要先把长文本切成较小的"块"（chunk）。这是因为嵌入模型对输入长度有限制（通常 512 个 Token），而且较小的文本块在语义搜索时匹配精度更高。分块的质量直接影响搜索效果——块太大，一段文字包含太多主题，搜索不精准；块太小，丢失上下文信息，搜索结果不完整。

### 6.1 固定长度分块

最简单的分块方式，按固定字符数切割。优点是实现简单、分块大小均匀；缺点是可能在句子中间截断，破坏语义完整性。适合对精度要求不高的场景。

```python
def fixed_chunk(text: str, chunk_size: int = 500) -> list[str]:
    """按固定字符数切分"""
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
```

### 6.2 智能分块（推荐）

在句子边界处切分，并保留一定的重叠区域。重叠（overlap）的作用是：如果关键信息恰好跨越两个块的边界，重叠区域能确保这部分信息同时出现在两个块中，不会因为分块而丢失。这种分块方式在大多数场景下都能获得最好的搜索效果。

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

文本长度不同，最优的分块参数也不同。短文本（如 FAQ）适合较小的分块，保持每个块的主题单一；长文本（如技术手册）适合较大的分块，保留更多上下文。下表提供了不同文本长度下的推荐参数值：

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
| 中文搜索效果差 | 默认英文嵌入模型 | 创建集合时指定中文嵌入模型（如 `BAAI/bge-small-zh-v1.5`） |
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
