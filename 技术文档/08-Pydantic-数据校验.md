# Pydantic — 数据校验与配置管理技术文档

---

## 1. 技术概述

Pydantic 是 Python 的数据校验库，使用 Python 类型注解定义数据结构，自动完成类型转换、数据校验和序列化。本项目用于 API 请求/响应模型和配置管理。

| 项目 | 说明 |
|------|------|
| 版本 | 2.9.0 |
| 语言 | Python |
| 官方文档 | https://docs.pydantic.dev/ |
| 安装 | `pip install pydantic==2.9.0` |
| 核心功能 | 数据校验、类型转换、序列化、配置管理 |

---

## 2. 核心概念

### 2.1 BaseModel — 数据模型

```python
from pydantic import BaseModel, Field
from typing import Optional

class ChatRequest(BaseModel):
    message: str                          # 必填字符串
    thread_id: Optional[str] = None       # 可选字符串
    user_id: str = "default"              # 带默认值的字符串

# 自动校验和类型转换
req = ChatRequest(message=123)  # 传入 int，自动转为 str
print(req.message)              # "123"
print(req.user_id)              # "default"

# 校验失败抛出异常
try:
    ChatRequest()  # message 是必填的
except Exception as e:
    print(e)  # 缺少 message 字段
```

### 2.2 Field — 字段约束

```python
from pydantic import BaseModel, Field

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="搜索查询")
    top_k: int = Field(default=5, ge=1, le=50, description="返回数量")
    threshold: float = Field(default=0.5, gt=0.0, lt=1.0)

# Field 参数：
# ...          表示必填
# default      默认值
# min_length   最小长度（字符串）
# max_length   最大长度（字符串）
# ge / gt      大于等于 / 大于（数值）
# le / lt      小于等于 / 小于（数值）
# description  字段描述（用于 API 文档）
```

---

## 3. 在 FastAPI 中使用

Pydantic 是 FastAPI 的核心依赖，直接定义 API 的请求和响应格式：

```python
from fastapi import FastAPI
from pydantic import BaseModel, Field
from typing import Optional

app = FastAPI()

# === 请求模型 ===
class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    thread_id: Optional[str] = Field(default=None, description="会话ID")
    user_id: str = Field(default="default", description="用户ID")

class KnowledgeImportRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    source: str = Field(default="manual")

class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)

# === 响应模型 ===
class ChatResponse(BaseModel):
    code: int = 200
    result: str
    thread_id: Optional[str] = None

# === 使用 ===
@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    # request 已经被 Pydantic 校验过，类型安全
    answer = process_message(request.message)
    return ChatResponse(result=answer, thread_id=request.thread_id)
```

**FastAPI 自动完成：**
1. 根据 Pydantic Model 校验请求体
2. 校验失败返回 422 + 详细错误信息
3. 自动生成 Swagger/ReDoc API 文档
4. 序列化响应为 JSON

---

## 4. 配置管理（BaseSettings）

### 4.1 安装 pydantic-settings

```bash
pip install pydantic-settings
```

### 4.2 定义配置类

```python
# config/settings.py
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # LLM 配置
    LLM_PROVIDER: str = "openai"
    LLM_MODEL: str = "gpt-3.5-turbo"
    LLM_API_KEY: Optional[str] = None
    LLM_API_BASE: Optional[str] = None
    LLM_TEMPERATURE: float = 0.7
    LLM_MAX_TOKENS: int = 2000

    # 嵌入模型
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # 向量搜索
    VECTOR_SEARCH_LIMIT: int = 5

    # 文本分块
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50

    # 运行配置
    DEBUG: bool = False
    MAX_HISTORY_MESSAGES: int = 20

    class Config:
        env_file = ".env"            # 从 .env 文件加载
        env_file_encoding = "utf-8"

# 全局单例
settings = Settings()
```

### 4.3 .env 文件

```env
# .env
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
LLM_API_KEY=sk-your-key-here
LLM_API_BASE=https://api.deepseek.com/v1
LLM_TEMPERATURE=0.7
DEBUG=true
```

### 4.4 使用配置

```python
from config.settings import settings

# 直接访问属性（带类型提示和自动转换）
print(settings.LLM_PROVIDER)       # "deepseek"
print(settings.LLM_TEMPERATURE)    # 0.7 (float)
print(settings.DEBUG)              # True (bool)
print(settings.MAX_HISTORY_MESSAGES)  # 20 (int)
```

---

## 5. 模型序列化

```python
from pydantic import BaseModel
from typing import Optional

class User(BaseModel):
    name: str
    age: int
    email: Optional[str] = None

user = User(name="张三", age=25, email="zhang@example.com")

# 转 JSON 字符串
json_str = user.model_dump_json()
print(json_str)  # {"name":"张三","age":25,"email":"zhang@example.com"}

# 转字典
data = user.model_dump()
print(data)  # {"name": "张三", "age": 25, "email": "zhang@example.com"}

# 排除字段
data_partial = user.model_dump(exclude={"email"})
print(data_partial)  # {"name": "张三", "age": 25}

# 从字典创建
user2 = User.model_validate({"name": "李四", "age": 30})
```

---

## 6. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| `ValidationError` | 数据类型不匹配 | 检查输入类型和 Field 约束 |
| .env 不生效 | 文件路径不对 | 确认 `.env` 在工作目录下 |
| bool 类型读取为字符串 | 环境变量都是字符串 | Pydantic 会自动转换，确认版本 ≥ 2.0 |
| 嵌套模型不生效 | 未正确嵌套 | 使用 `model_config` 配置 |
