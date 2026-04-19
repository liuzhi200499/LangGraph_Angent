import asyncio
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from sse_starlette.sse import EventSourceResponse

router = APIRouter(prefix="/api")


# === 数据模型 ===

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = None
    user_id: str = "default"


class ChatResponse(BaseModel):
    code: int = 200
    result: str
    thread_id: str


class KnowledgeImportRequest(BaseModel):
    title: str
    content: str
    source: str = "manual"


class KnowledgeSearchRequest(BaseModel):
    query: str
    top_k: int = 5


# === 健康检查 ===

@router.get("/health")
async def health_check():
    return {"code": 200, "msg": "Agent服务运行正常"}


# === 对话接口 ===

@router.post("/chat")
async def chat(req: ChatRequest):
    from services.chat_service import ChatService
    service = ChatService()
    loop = asyncio.get_event_loop()
    result, thread_id = await loop.run_in_executor(
        None, service.chat, req.message, req.thread_id, req.user_id
    )
    return {"code": 200, "result": result, "thread_id": thread_id}


@router.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    from services.chat_service import ChatService
    service = ChatService()

    async def event_generator():
        for chunk in service.chat_stream(req.message, req.thread_id, req.user_id):
            yield {"data": f'{{"content": "{chunk}"}}'}
        yield {"data": '{"content": "[DONE]"}'}

    return EventSourceResponse(event_generator())


@router.get("/conversation/{thread_id}")
async def get_conversation(thread_id: str):
    from db.sqlite_manager import sqlite_manager
    messages = sqlite_manager.load_messages(thread_id)
    return {"code": 200, "result": messages}


# === 知识库接口 ===

@router.post("/knowledge/import/text")
async def import_text(req: KnowledgeImportRequest):
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
    from services.knowledge_service import search_knowledge
    results = search_knowledge(req.query, req.top_k)
    return {"code": 200, "result": results}


@router.get("/knowledge/stats")
async def knowledge_stats():
    from services.knowledge_service import get_knowledge_stats
    stats = get_knowledge_stats()
    return {"code": 200, "result": stats}
