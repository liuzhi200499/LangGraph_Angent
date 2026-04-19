from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Agent 智能体 API",
    version="1.0.0",
    description="基于 LangGraph 的智能知识库问答系统",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

from api.routes import router
app.include_router(router)


@app.get("/")
async def root():
    return {"code": 200, "msg": "Agent 智能体 API 服务"}
