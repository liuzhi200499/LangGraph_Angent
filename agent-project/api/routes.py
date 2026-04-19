"""
API 路由定义模块
定义所有 RESTful API 接口，包括：
- 健康检查
- 同步对话 / SSE 流式对话
- 对话历史查询
- 知识库导入 / 搜索 / 统计

使用延迟导入（函数内 import）避免循环依赖问题。
"""
import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from sse_starlette.sse import EventSourceResponse

# 创建路由器，所有接口统一使用 /api 前缀
router = APIRouter(prefix="/api")


# ==================== 请求/响应数据模型 ====================

class ChatRequest(BaseModel):
    """对话请求模型"""
    message: str                          # 用户消息内容（必填）
    thread_id: Optional[str] = None       # 会话线程ID（为空则创建新会话）
    user_id: str = "default"              # 用户标识


class ChatResponse(BaseModel):
    """对话响应模型"""
    code: int = 200                       # 状态码
    result: str                           # AI 回复内容
    thread_id: str                        # 会话线程ID


class KnowledgeImportRequest(BaseModel):
    """知识导入请求模型"""
    title: str                            # 文档标题（必填）
    content: str                          # 文档正文（必填）
    source: str = "manual"                # 来源标记


class KnowledgeSearchRequest(BaseModel):
    """知识搜索请求模型"""
    query: str                            # 搜索查询文本（必填）
    top_k: int = 5                        # 返回结果数量


# ==================== 健康检查接口 ====================

@router.get("/health")
async def health_check():
    """健康检查接口，用于监控系统和负载均衡器探测服务状态"""
    return {"code": 200, "msg": "Agent服务运行正常"}


# ==================== 对话接口 ====================

@router.post("/chat")
async def chat(req: ChatRequest):
    """
    同步对话接口
    接收用户消息，调用 Agent 获取完整回复。
    使用 run_in_executor 将同步的 Agent 调用转为异步，避免阻塞事件循环。
    """
    from services.chat_service import ChatService
    service = ChatService()
    loop = asyncio.get_event_loop()
    # 在线程池中执行同步的 chat 方法
    result, thread_id = await loop.run_in_executor(
        None, service.chat, req.message, req.thread_id, req.user_id
    )
    return {"code": 200, "result": result, "thread_id": thread_id}


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    """
    SSE 流式对话接口
    通过 Server-Sent Events 逐块推送回复内容，实现打字机效果。
    前端使用 EventSource API 接收流式数据。
    """
    from services.chat_service import ChatService
    service = ChatService()

    async def event_generator():
        # 将同步生成器中的每个文本块作为 SSE 事件推送
        for chunk in service.chat_stream(req.message, req.thread_id, req.user_id):
            yield {"data": f'{{"content": "{chunk}"}}'}
        # 发送结束标记，前端据此判断流式输出完成
        yield {"data": '{"content": "[DONE]"}'}

    return EventSourceResponse(event_generator())


@router.get("/conversation/{thread_id}")
async def get_conversation(thread_id: str):
    """获取指定会话的对话历史记录"""
    from db.sqlite_manager import sqlite_manager
    messages = sqlite_manager.load_messages(thread_id)
    return {"code": 200, "result": messages}


# ==================== 知识库接口 ====================

@router.post("/knowledge/import/text")
async def import_text(req: KnowledgeImportRequest):
    """
    导入文本知识到知识库
    处理流程：文本分块 → 向量化 → 存入 MenteeDB
    """
    from services.knowledge_service import import_knowledge
    doc_id, chunk_count = import_knowledge(req.title, req.content, req.source)
    return {
        "code": 200,
        "result": {
            "doc_id": doc_id,
            "chunk_count": chunk_count,
            "message": "知识导入成功",
        },
    }


@router.post("/knowledge/search")
async def search_knowledge(req: KnowledgeSearchRequest):
    """在知识库中进行语义搜索，返回最相关的知识片段"""
    from services.knowledge_service import search_knowledge
    results = search_knowledge(req.query, req.top_k)
    return {"code": 200, "result": results}


@router.get("/knowledge/stats")
async def knowledge_stats():
    """获取知识库统计数据（活跃文档数、知识分块数）"""
    from services.knowledge_service import get_knowledge_stats
    stats = get_knowledge_stats()
    return {"code": 200, "result": stats}
