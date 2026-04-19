"""
FastAPI 应用入口
创建 FastAPI 应用实例，配置 CORS 跨域中间件，挂载路由。
启动命令：uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 创建 FastAPI 应用实例
app = FastAPI(
    title="Agent 智能体 API",
    version="1.0.0",
    description="基于 LangGraph 的智能知识库问答系统",
)

# 配置 CORS 跨域中间件，允许前端应用访问 API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 允许所有来源（生产环境应限制具体域名）
    allow_methods=["*"],      # 允许所有 HTTP 方法
    allow_headers=["*"],      # 允许所有请求头
)

# 注册路由模块（所有 /api/* 路径的接口定义）
from api.routes import router
app.include_router(router)


@app.get("/")
async def root():
    """根路径，返回 API 服务基本信息"""
    return {"code": 200, "msg": "Agent 智能体 API 服务"}
