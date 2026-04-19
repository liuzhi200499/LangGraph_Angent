# MenteeDB — 向量数据库技术文档

---

## 1. 技术概述

MenteeDB 是一个轻量级本地向量数据库，专为 AI 应用设计。它内置文本向量化能力，支持语义搜索，无需额外部署向量计算服务，数据全部存储在本地文件系统中。

| 项目 | 说明 |
|------|------|
| 版本 | 0.2.0 |
| 语言 | Python |
| 安装 | `pip install menteedb==0.2.0` |
| 数据存储 | 本地文件系统 |
| 核心能力 | 自动向量化、语义搜索、批量操作 |

---

## 2. 为什么选择 MenteeDB

| 特性 | MenteeDB | Chroma | Pinecone | Milvus |
|------|----------|--------|----------|--------|
| 部署方式 | 本地文件 | 本地/服务 | 云服务 | 自建服务 |
| 内置嵌入 | 有 | 有 | 无 | 无 |
| 额外依赖 | 无 | 少量 | 账号+网络 | 重量级 |
| 适合场景 | 轻量原型/个人 | 中小项目 | 生产云部署 | 大规模生产 |

本项目选择 MenteeDB 的原因：**零配置、纯本地、开箱即用**。

---

## 3. 安装与初始化

### 3.1 安装

```bash
pip install menteedb==0.2.0
```

### 3.2 初始化数据库

```python
from menteedb import MenteeDB

# 创建数据库实例（指定数据存储目录）
db = MenteeDB(
    persist_directory="./data/agent_memory",
    embedding_model="all-MiniLM-L6-v2"  # 自动下载嵌入模型（~80MB）
)

print("MenteeDB 初始化完成")
```

**首次运行时会自动下载嵌入模型，后续使用本地缓存。**

### 3.3 数据目录结构

```
data/agent_memory/
├── chroma.sqlite3              # 元数据存储
├── embeddings_cache/           # 向量缓存
└── config.json                 # 数据库配置
```

---

## 4. 核心使用流程

### 4.1 完整使用流程图

```
创建表 → 插入数据（自动向量化） → 语义搜索 → 获取结果
  │           │                      │           │
  ▼           ▼                      ▼           ▼
 定义字段   content 字段           输入查询     返回相似度
 和类型     自动索引              文本          排序结果
```

### 4.2 第一步：创建表

```python
# 创建向量表（指定字段名，content 字段会自动建立向量索引）
db.create_table(
    table_name="knowledge_chunks",
    fields=["doc_id", "chunk_id", "title", "content", "metadata"]
)
```

**关键规则：**
- 表中必须有一个 `content` 字段（或指定的文本字段），该字段的内容会被自动向量化
- 其他字段作为元数据存储，用于过滤和展示

### 4.3 第二步：插入数据

#### 单条插入

```python
db.insert(
    table_name="knowledge_chunks",
    record={
        "doc_id": "doc_001",
        "chunk_id": "doc_001_0",
        "title": "机器学习入门",
        "content": "机器学习是人工智能的一个分支，它使计算机能够从数据中学习。",
        "metadata": '{"chunk_index": 0, "source": "wiki"}'
    }
)
```

#### 批量插入

```python
records = [
    {
        "doc_id": "doc_001",
        "chunk_id": f"doc_001_{i}",
        "title": "机器学习入门",
        "content": chunk_text,
        "metadata": f'{{"chunk_index": {i}, "source": "wiki"}}'
    }
    for i, chunk_text in enumerate(text_chunks)
]

db.batch_insert("knowledge_chunks", records)
print(f"已插入 {len(records)} 条记录")
```

### 4.4 第三步：语义搜索

```python
results = db.search(
    table_name="knowledge_chunks",
    query_text="什么是机器学习？",    # 查询文本（会自动向量化）
    limit=5                          # 返回最相似的 5 条结果
)

for result in results:
    print(f"相似度: {result['score']:.4f}")
    print(f"标题: {result['title']}")
    print(f"内容: {result['content'][:100]}...")
    print("---")
```

**输出示例：**
```
相似度: 0.8923
标题: 机器学习入门
内容: 机器学习是人工智能的一个分支，它使计算机能够从数据中学习。...
---
相似度: 0.7856
标题: 深度学习概述
内容: 深度学习是机器学习的一个子集，使用多层神经网络进行学习。...
---
```

### 4.5 第四步：更新和删除

```python
# 更新记录
db.update(
    table_name="knowledge_chunks",
    filters={"chunk_id": "doc_001_0"},
    updates={"title": "机器学习入门（修订版）"}
)

# 删除记录
db.delete(
    table_name="knowledge_chunks",
    filters={"doc_id": "doc_001"}
)

# 清空表
db.truncate("knowledge_chunks")
```

---

## 5. 在项目中集成 MenteeDB

### 5.1 封装向量数据库管理器

```python
# db/vector_manager.py
import json
from menteedb import MenteeDB
from config.settings import settings

class VectorManager:
    def __init__(self):
        self.db = MenteeDB(
            persist_directory="./data/agent_memory",
            embedding_model=settings.EMBEDDING_MODEL
        )
        self.table_name = "knowledge_chunks"
        self._ensure_table()

    def _ensure_table(self):
        """确保表存在"""
        self.db.create_table(
            table_name=self.table_name,
            fields=["doc_id", "chunk_id", "title", "content", "metadata"]
        )

    def import_document(self, doc_id: str, title: str, chunks: list[str],
                        source: str = "manual"):
        """导入文档（批量插入分块后的文本）"""
        records = [
            {
                "doc_id": doc_id,
                "chunk_id": f"{doc_id}_{i}",
                "title": title,
                "content": chunk,
                "metadata": json.dumps({
                    "chunk_index": i,
                    "source": source,
                    "total_chunks": len(chunks)
                })
            }
            for i, chunk in enumerate(chunks)
        ]
        self.db.batch_insert(self.table_name, records)
        return len(records)

    def search(self, query: str, top_k: int = None) -> list[dict]:
        """语义搜索"""
        top_k = top_k or settings.VECTOR_SEARCH_LIMIT
        results = self.db.search(
            table_name=self.table_name,
            query_text=query,
            limit=top_k
        )
        return results

    def delete_document(self, doc_id: str):
        """删除文档的所有分块"""
        self.db.delete(
            table_name=self.table_name,
            filters={"doc_id": doc_id}
        )

    def get_stats(self) -> dict:
        """获取知识库统计"""
        # 具体实现取决于 MenteeDB API
        return {"table": self.table_name}
```

### 5.2 作为 LangGraph 工具使用

```python
from langchain_core.tools import tool

vector_mgr = VectorManager()

@tool
def search_knowledge(query: str, top_k: int = 5) -> str:
    """在知识库中搜索与查询最相关的内容"""
    results = vector_mgr.search(query, top_k)

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
            # 在 chunk_size 附近查找最佳切分点
            for sep in ['。', '！', '？', '；', '\n', '.', '!', '?', ';']:
                pos = text.rfind(sep, start + chunk_size - overlap, end + overlap)
                if pos != -1:
                    end = pos + 1
                    break
        chunks.append(text[start:end].strip())
        start = end - overlap  # 重叠部分确保上下文连续

    return [c for c in chunks if c]  # 过滤空块
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
| 内存占用高 | 数据量过大 | 控制单表记录数量，定期清理 |
| 中文搜索效果差 | 嵌入模型不适配 | 换用 `text2vec-large-chinese` 模型 |
| 数据丢失 | 未正确持久化 | 确认 `persist_directory` 路径可写 |

---

## 8. 备份与迁移

```bash
# 备份：直接复制数据目录
cp -r data/agent_memory/ backup/agent_memory_20260419/

# 恢复：将备份目录设为 persist_directory
db = MenteeDB(persist_directory="./backup/agent_memory_20260419")

# 迁移：打包数据目录后在新环境中解压到相同路径
tar -czf agent_memory.tar.gz data/agent_memory/
```
