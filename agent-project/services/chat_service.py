"""
对话服务模块
封装 Agent 的对话逻辑，提供同步和流式两种对话模式。
负责管理对话线程（thread_id）和消息持久化。
"""
import uuid
from langchain_core.messages import HumanMessage
from core.graph import build_agent_graph
from db.sqlite_manager import sqlite_manager


class ChatService:
    """
    对话服务类
    - 管理与 LangGraph Agent 的交互
    - 处理对话上下文的持久化（SQLite 存储）
    - 支持多会话隔离（通过 thread_id）
    """

    def __init__(self):
        # 构建并编译 LangGraph Agent 工作流
        self.agent = build_agent_graph()

    def chat(self, message: str, thread_id: str = None, user_id: str = "default") -> tuple[str, str]:
        """
        同步对话接口
        调用 Agent 获取完整回复后一次性返回。

        参数:
            message: 用户输入的消息文本
            thread_id: 会话线程ID，为空时自动创建新会话
            user_id: 用户标识，默认为 'default'
        返回:
            (AI 回复文本, 会话线程ID)
        """
        # 如果没有 thread_id，生成一个新的 UUID 作为新会话
        if not thread_id:
            thread_id = str(uuid.uuid4())

        # LangGraph 通过 thread_id 隔离不同会话的状态（MemorySaver）
        config = {"configurable": {"thread_id": thread_id}}

        # 调用 Agent 图，传入用户消息
        result = self.agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )

        # 将用户消息和 AI 回复持久化到 SQLite
        sqlite_manager.save_message(thread_id, user_id, "user", message)
        ai_response = result["messages"][-1].content  # 取最后一条消息（即 AI 回复）
        sqlite_manager.save_message(thread_id, user_id, "assistant", ai_response)

        return ai_response, thread_id

    def chat_stream(self, message: str, thread_id: str = None, user_id: str = "default"):
        """
        SSE 流式对话接口
        逐块生成回复内容，通过 yield 返回给前端实现打字机效果。

        参数:
            message: 用户输入的消息文本
            thread_id: 会话线程ID
            user_id: 用户标识
        返回:
            生成器，逐块 yield 回复文本片段
        """
        if not thread_id:
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}

        # 先保存用户消息
        sqlite_manager.save_message(thread_id, user_id, "user", message)

        # 流式调用 Agent，逐块获取回复
        full_response = ""
        for chunk in self.agent.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        ):
            # 只处理 agent 节点的输出（跳过 tools 节点）
            if "agent" in chunk:
                msg = chunk["agent"]["messages"][-1]
                content = msg.content if hasattr(msg, "content") else str(msg)
                if content:
                    full_response += content  # 拼接完整回复
                    yield content             # 逐块返回给调用方

        # 流式结束后，将完整的 AI 回复保存到数据库
        if full_response:
            sqlite_manager.save_message(thread_id, user_id, "assistant", full_response)

    def get_history(self, thread_id: str) -> list[dict]:
        """获取指定会话的对话历史记录"""
        return sqlite_manager.load_messages(thread_id)
