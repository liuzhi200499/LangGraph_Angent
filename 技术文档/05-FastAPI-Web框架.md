# FastAPI — Web 框架技术文档

---

## 1. 技术概述

FastAPI 是一个高性能的 Python Web 框架，基于标准 Python 类型提示构建，自动生成交互式 API 文档，原生支持异步请求处理。

| 项目 | 说明 |
|------|------|
| 版本 | 0.115.0 |
| 语言 | Python |
| 官方文档 | https://fastapi.tiangolo.com/zh/ |
| 安装 | `pip install fastapi==0.115.0 uvicorn==0.30.0` |
| ASGI 服务器 | uvicorn |
| 核心特点 | 自动文档、类型校验、异步原生、高性能 |

---

## 2. 安装与运行

### 2.1 安装

```bash
pip install fastapi==0.115.0 uvicorn==0.30.0 sse-starlette==2.1.0
```

### 2.2 最小应用

```python
# api/main.py
from fastapi import FastAPI

app = FastAPI(title="Agent API", version="1.0.0")

@app.get("/")
def root():
    return {"message": "Agent 服务运行中"}
```

### 2.3 启动服务

```bash
# 开发模式（自动重载）
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# 生产模式
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### 2.4 访问自动文档

启动后访问：
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 3. 核心使用流程

### 3.1 路由与请求方法

```python
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI()

# GET 请求
@app.get("/api/health")
def health_check():
    return {"code": 200, "msg": "服务运行正常"}

# POST 请求（带请求体）
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    user_id: str = "default"

@app.post("/api/chat")
def chat(request: ChatRequest):
    response = f"收到消息: {request.message}"
    return {"code": 200, "result": response, "thread_id": request.thread_id}

# 路径参数
@app.get("/api/conversation/{thread_id}")
def get_conversation(thread_id: str):
    return {"thread_id": thread_id, "messages": []}

# 查询参数
@app.get("/api/knowledge/search")
def search_knowledge(query: str, top_k: int = 5):
    return {"query": query, "results": []}
```

### 3.2 请求参数类型

| 参数类型 | 声明方式 | 示例 |
|---------|---------|------|
| 路径参数 | `{param}` in path | `@app.get("/items/{item_id}")` |
| 查询参数 | 函数参数（有默认值） | `def list(limit: int = 10)` |
| 请求体 | Pydantic Model | `def create(item: ItemModel)` |
| 请求头 | `Header()` | `def get(token: str = Header())` |

### 3.3 响应模型

```python
from pydantic import BaseModel
from typing import Optional

class ChatResponse(BaseModel):
    code: int = 200
    result: str
    thread_id: Optional[str] = None

@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        result="这是回答",
        thread_id=request.thread_id
    )
```

### 3.4 中间件

```python
from fastapi.middleware.cors import CORSMiddleware

# CORS 跨域支持（前后端分离必需）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # 生产环境应指定具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

---

## 4. SSE 流式输出

Server-Sent Events（SSE）是实现 LLM 流式响应的标准方式：

### 4.1 SSE 接口实现

```python
from sse_starlette.sse import EventSourceResponse
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class StreamRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None

@app.post("/api/chat/stream")
async def chat_stream(request: StreamRequest):
    """SSE 流式对话接口"""
    async def event_generator():
        # 模拟流式 LLM 输出
        words = ["深度", "学习", "是", "机器", "学习", "的", "一个", "子集"]
        for word in words:
            yield {
                "event": "message",
                "data": json.dumps({"content": word}, ensure_ascii=False)
            }
        yield {"event": "message", "data": "[DONE]"}

    return EventSourceResponse(event_generator())
```

### 4.2 客户端接收 SSE

```javascript
// JavaScript 前端
const eventSource = new EventSource("/api/chat/stream");
eventSource.onmessage = (event) => {
    if (event.data === "[DONE]") {
        eventSource.close();
    } else {
        const data = JSON.parse(event.data);
        document.getElementById("output").textContent += data.content;
    }
};
```

```python
# Python 客户端
import requests

response = requests.post(
    "http://localhost:8000/api/chat/stream",
    json={"message": "解释深度学习"},
    stream=True
)
for line in response.iter_lines():
    if line:
        print(line.decode())
```

---

## 5. 完整项目 API 实现

### 5.1 项目入口

```python
# api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Agent 智能体 API",
    version="1.0.0",
    description="基于 LangGraph 的智能知识库问答系统"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
from api.routes import router
app.include_router(router)

@app.on_event("startup")
async def startup():
    """应用启动时初始化"""
    print("Agent 服务启动中...")
    # 初始化数据库、加载模型等

@app.on_event("shutdown")
async def shutdown():
    """应用关闭时清理"""
    print("Agent 服务关闭")
```

### 5.2 路由定义

```python
# api/routes.py
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api")

# --- 数据模型 ---
class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    user_id: str = "default"

class KnowledgeImportRequest(BaseModel):
    title: str
    content: str
    source: str = "manual"

class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5

# --- 接口 ---
@router.get("/health")
def health():
    return {"code": 200, "msg": "Agent服务运行正常"}

@router.post("/chat")
def chat(request: ChatRequest):
    from services.chat_service import ChatService
    service = ChatService()
    result, thread_id = service.chat(
        request.message, request.thread_id, request.user_id
    )
    return {"code": 200, "result": result, "thread_id": thread_id}

@router.post("/knowledge/import/text")
def import_text(request: KnowledgeImportRequest):
    from services.knowledge_service import KnowledgeService
    service = KnowledgeService()
    doc_id, chunk_count = service.import_text(
        request.title, request.content, request.source
    )
    return {"code": 200, "result": {"doc_id": doc_id, "chunk_count": chunk_count}}

@router.post("/knowledge/search")
def search_knowledge(request: KnowledgeSearchRequest):
    from services.knowledge_service import KnowledgeService
    service = KnowledgeService()
    results = service.search(request.query, request.top_k)
    return {"code": 200, "result": results}

@router.get("/knowledge/stats")
def knowledge_stats():
    from services.knowledge_service import KnowledgeService
    service = KnowledgeService()
    return {"code": 200, "result": service.get_stats()}
```

---

## 6. 错误处理

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

app = FastAPI()

class AppException(Exception):
    def __init__(self, code: int, msg: str):
        self.code = code
        self.msg = msg

@app.exception_handler(AppException)
async def app_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.code,
        content={"code": exc.code, "msg": exc.msg}
    )

# 使用
@app.post("/api/chat")
def chat(request: ChatRequest):
    if not request.message.strip():
        raise AppException(400, "消息不能为空")
    # ...
```

---

## 7. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 422 Unprocessable Entity | 请求体格式不符 | 检查 Pydantic Model 字段类型 |
| CORS 被阻止 | 未配置跨域 | 添加 `CORSMiddleware` |
| SSE 中断 | Nginx 缓冲 | 设置 `proxy_buffering off` |
| 启动报错端口占用 | 端口冲突 | 更换 `--port` 或关闭占用进程 |
| 异步函数报错 | 混用 sync/async | 统一使用 async def 或 def |
