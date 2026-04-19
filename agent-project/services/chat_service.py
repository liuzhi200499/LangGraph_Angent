import uuid
from langchain_core.messages import HumanMessage
from core.graph import build_agent_graph
from db.sqlite_manager import sqlite_manager


class ChatService:
    def __init__(self):
        self.agent = build_agent_graph()

    def chat(self, message: str, thread_id: str = None, user_id: str = "default") -> tuple[str, str]:
        """同步对话接口"""
        if not thread_id:
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}
        result = self.agent.invoke(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        )

        sqlite_manager.save_message(thread_id, user_id, "user", message)
        ai_response = result["messages"][-1].content
        sqlite_manager.save_message(thread_id, user_id, "assistant", ai_response)

        return ai_response, thread_id

    def chat_stream(self, message: str, thread_id: str = None, user_id: str = "default"):
        """SSE 流式对话接口"""
        if not thread_id:
            thread_id = str(uuid.uuid4())

        config = {"configurable": {"thread_id": thread_id}}
        sqlite_manager.save_message(thread_id, user_id, "user", message)

        full_response = ""
        for chunk in self.agent.stream(
            {"messages": [HumanMessage(content=message)]},
            config=config,
        ):
            if "agent" in chunk:
                msg = chunk["agent"]["messages"][-1]
                content = msg.content if hasattr(msg, "content") else str(msg)
                if content:
                    full_response += content
                    yield content

        if full_response:
            sqlite_manager.save_message(thread_id, user_id, "assistant", full_response)

    def get_history(self, thread_id: str) -> list[dict]:
        return sqlite_manager.load_messages(thread_id)
