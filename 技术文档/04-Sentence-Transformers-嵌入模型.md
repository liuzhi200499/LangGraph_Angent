# Sentence-Transformers — 文本嵌入模型技术文档

---

## 1. 技术概述

Sentence-Transformers 是一个用于生成**语义向量**的 Python 库，它将文本转换为固定维度的数值向量，使语义相近的文本在向量空间中距离更近。这是实现语义搜索、文本聚类、相似度计算等任务的基础。

| 项目 | 说明 |
|------|------|
| 版本 | 3.0.0 |
| 语言 | Python |
| 官方文档 | https://www.sbert.net/ |
| 安装 | `pip install sentence-transformers==3.0.0` |
| 核心功能 | 文本向量化、语义相似度计算 |

---

## 2. 什么是文本嵌入

```
"机器学习是AI的分支"  →  [0.23, -0.15, 0.87, ..., 0.12]  (384维向量)
"深度学习是AI的分支"  →  [0.21, -0.14, 0.85, ..., 0.11]  (相似！距离很近)
"今天天气真好"        →  [0.05, 0.88, -0.32, ..., 0.67]  (不相关，距离远)
```

嵌入模型将文本映射到一个高维数学空间中：
- **语义相似的文本** → 向量距离近（余弦相似度高）
- **语义不同的文本** → 向量距离远（余弦相似度低）

---

## 3. 安装与配置

### 3.1 安装

```bash
pip install sentence-transformers==3.0.0
# 会自动安装 PyTorch 作为后端
```

### 3.2 验证安装

```python
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("all-MiniLM-L6-v2")
print(f"模型加载成功，向量维度: {model.get_sentence_embedding_dimension()}")
# 输出：模型加载成功，向量维度: 384
```

---

## 4. 模型选择

### 4.1 推荐模型对比

| 模型名 | 大小 | 向量维度 | 速度 | 适用场景 |
|--------|------|---------|------|---------|
| `all-MiniLM-L6-v2` | ~80MB | 384 | 快 | 轻量本地部署（推荐本项目） |
| `all-mpnet-base-v2` | ~420MB | 768 | 中 | 更高精度要求 |
| `paraphrase-multilingual-MiniLM-L12-v2` | ~470MB | 384 | 中 | 多语言（含中文） |
| `text2vec-large-chinese` | ~1.2GB | 1024 | 慢 | 纯中文场景 |

### 4.2 选择建议

```
你的项目是？
├── 原型开发/本地部署 → all-MiniLM-L6-v2（快、小、够用）
├── 中文为主的内容   → paraphrase-multilingual-MiniLM-L12-v2
├── 追求最高精度     → all-mpnet-base-v2
└── 纯中文生产环境   → text2vec-large-chinese
```

---

## 5. 核心使用方法

### 5.1 加载模型

```python
from sentence_transformers import SentenceTransformer

# 方式一：加载在线模型（首次自动下载，后续使用缓存）
model = SentenceTransformer("all-MiniLM-L6-v2")

# 方式二：加载本地模型
model = SentenceTransformer("./local_model/all-MiniLM-L6-v2")
```

**模型缓存位置：**
- Windows: `C:\Users\{用户名}\.cache\huggingface\hub\`
- macOS/Linux: `~/.cache/huggingface/hub/`

### 5.2 生成文本向量

```python
# 单条文本
embedding = model.encode("机器学习是人工智能的一个分支")
print(f"向量维度: {embedding.shape}")     # (384,)
print(f"向量前5维: {embedding[:5]}")       # [0.023, -0.015, ...]

# 批量文本（推荐，性能更好）
texts = [
    "机器学习是人工智能的一个分支",
    "深度学习是机器学习的子集",
    "今天天气很好"
]
embeddings = model.encode(texts)
print(f"批量向量维度: {embeddings.shape}")  # (3, 384)
```

### 5.3 计算语义相似度

```python
from sentence_transformers import util

text1 = "什么是机器学习？"
text2 = "解释一下 ML"
text3 = "今天中午吃什么"

# 生成向量
e1 = model.encode(text1)
e2 = model.encode(text2)
e3 = model.encode(text3)

# 计算余弦相似度
sim_12 = util.cos_sim(e1, e2).item()
sim_13 = util.cos_sim(e1, e3).item()

print(f"'{text1}' vs '{text2}': {sim_12:.4f}")  # ~0.75（语义相近）
print(f"'{text1}' vs '{text3}': {sim_13:.4f}")  # ~0.05（不相关）
```

### 5.4 语义搜索

```python
from sentence_transformers import util

# 知识库文档
documents = [
    "Python 是一种通用编程语言，由 Guido van Rossum 创建。",
    "JavaScript 是 Web 开发中最常用的编程语言。",
    "机器学习通过数据训练模型来做出预测。",
    "深度学习使用多层神经网络处理复杂模式。",
    "自然语言处理让计算机理解人类语言。"
]

# 预先计算文档向量（只需做一次）
doc_embeddings = model.encode(documents)

# 用户查询
query = "谁发明了 Python？"
query_embedding = model.encode(query)

# 计算相似度并排序
similarities = util.cos_sim(query_embedding, doc_embeddings)[0]
top_results = sorted(
    zip(range(len(documents)), similarities),
    key=lambda x: x[1], reverse=True
)

for idx, score in top_results[:3]:
    print(f"[{score:.4f}] {documents[idx]}")

# 输出：
# [0.8234] Python 是一种通用编程语言，由 Guido van Rossum 创建。
# [0.3456] JavaScript 是 Web 开发中最常用的编程语言。
# [0.2134] 机器学习通过数据训练模型来做出预测。
```

---

## 6. 在项目中集成

### 6.1 封装嵌入服务

```python
# services/embedding_service.py
from sentence_transformers import SentenceTransformer, util
from config.settings import settings

class EmbeddingService:
    _instance = None

    def __new__(cls):
        """单例模式，避免重复加载模型"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.model = SentenceTransformer(settings.EMBEDDING_MODEL)
        return cls._instance

    def encode(self, text: str) -> list[float]:
        """将文本转为向量"""
        return self.model.encode(text).tolist()

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化"""
        return self.model.encode(texts, show_progress_bar=False).tolist()

    def similarity(self, text1: str, text2: str) -> float:
        """计算两段文本的语义相似度"""
        e1 = self.model.encode(text1)
        e2 = self.model.encode(text2)
        return util.cos_sim(e1, e2).item()

    def search(self, query: str, documents: list[str], top_k: int = 5) -> list[dict]:
        """语义搜索"""
        query_emb = self.model.encode(query)
        doc_embs = self.model.encode(documents)
        scores = util.cos_sim(query_emb, doc_embs)[0]

        results = sorted(
            [{"index": i, "text": documents[i], "score": scores[i].item()}
             for i in range(len(documents))],
            key=lambda x: x["score"], reverse=True
        )
        return results[:top_k]
```

### 6.2 使用示例

```python
emb = EmbeddingService()

# 向量化
vector = emb.encode("机器学习")
print(f"向量长度: {len(vector)}")  # 384

# 相似度
score = emb.similarity("机器学习", "深度学习")
print(f"相似度: {score:.4f}")      # ~0.75

# 语义搜索
docs = ["Python入门教程", "深度学习实战", "JavaScript指南", "AI研究报告"]
results = emb.search("人工智能", docs, top_k=2)
for r in results:
    print(f"[{r['score']:.4f}] {r['text']}")
```

---

## 7. 性能优化

### 7.1 批量编码

```python
# 慢：逐条编码
for text in texts:
    embedding = model.encode(text)  # 每次都有开销

# 快：批量编码
embeddings = model.encode(texts, batch_size=32, show_progress_bar=True)
```

### 7.2 模型预热

```python
# 应用启动时预加载模型，避免首次请求延迟
model = SentenceTransformer("all-MiniLM-L6-v2")
model.encode("warmup")  # 预热：触发首次计算
```

### 7.3 设备选择

```python
import torch

# 自动选择设备
device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("all-MiniLM-L6-v2", device=device)
```

---

## 8. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 首次运行下载慢 | HuggingFace 网络问题 | 设置 `HF_ENDPOINT=https://hf-mirror.com` 镜像 |
| 内存不足 | 模型过大 | 使用 `all-MiniLM-L6-v2`（仅 80MB） |
| 中文效果差 | 模型以英文为主 | 换用多语言或中文专用模型 |
| GPU 不可用 | 未安装 CUDA 版 PyTorch | `pip install torch --index-url https://download.pytorch.org/whl/cu118` |
| 编码速度慢 | 逐条处理 | 使用 `batch_size` 参数批量编码 |
