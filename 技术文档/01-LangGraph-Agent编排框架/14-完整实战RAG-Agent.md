# LangGraph — 完整实战：从零构建 RAG Agent

---

## 完整代码

下面是一个完整的、可运行的 RAG Agent 实现。它整合了前面所有文档讲到的概念：State、Node、Edge、ToolNode、Checkpointer、循环防护。代码按照功能模块分为六个部分：配置、工具定义、Agent 节点、图的构建、编译、运行入口。

```python
"""
LangGraph RAG Agent 完整实现
功能：知识库问答 + 多轮对话 + 工具调用
"""
import os
import uuid
from typing import Optional

from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.tools import tool
from langchain_core.messages import (
    HumanMessage, SystemMessage, AIMessage, ToolMessage
)
from pydantic import BaseModel, Field

# ============================================
# 1. 配置
# ============================================
# 系统提示词定义了 Agent 的角色、可用工具和行为规则。
# 这是 Agent 行为的"宪法"，LLM 在每次调用时都会看到它。
SYSTEM_PROMPT = """你是一个智能知识库助手。

你可以使用以下工具：
- search_knowledge: 在知识库中搜索信息
- get_current_time: 获取当前时间

工作原则：
1. 用户提问时，优先使用 search_knowledge 搜索知识库
2. 时间相关问题使用 get_current_time
3. 如果知识库没有相关信息，诚实告知用户
4. 回答要准确、简洁
"""

# ============================================
# 2. 工具定义
# ============================================
# 用 @tool 装饰器定义 Agent 可调用的工具函数。
# search_knowledge 使用 args_schema 提供精确的参数描述，
# get_current_time 用简单定义（无参数，自动推断）。
# 实际项目中，search_knowledge 应替换为真实的向量数据库查询。
class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    top_k: int = Field(default=5, description="返回结果数量")

@tool(args_schema=SearchInput)
def search_knowledge(query: str, top_k: int = 5) -> str:
    """在知识库中搜索与 query 相关的知识片段"""
    # 实际项目：results = vector_db.search(query, top_k)
    # 这里用模拟数据演示
    mock_db = {
        "python": "Python 由 Guido van Rossum 于 1991 年创建，是最流行的编程语言之一。",
        "机器学习": "机器学习是 AI 的分支，通过数据训练模型来做出预测和决策。",
        "深度学习": "深度学习是机器学习的子集，使用多层神经网络处理复杂模式。",
    }
    results = [v for k, v in mock_db.items() if k in query]
    return "\n".join(results) if results else "知识库中未找到相关内容。"

@tool
def get_current_time() -> str:
    """获取当前日期和时间"""
    from datetime import datetime
    return f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

ALL_TOOLS = [search_knowledge, get_current_time]

# ============================================
# 3. Agent 节点
# ============================================
# Agent 节点是整个图的核心，它做了以下事情：
#   a) 在消息列表前插入系统提示词
#   b) 裁剪过长的历史（保留最近 20 条）
#   c) 将 LangChain 消息格式转换为 LiteLLM/OpenAI 格式
#   d) 调用 LLM，传入工具定义
#   e) 将 LLM 返回的 tool_calls 从 OpenAI 格式转回 LangChain 格式
#
# 注意格式转换：LangGraph 内部使用 LangChain 的消息类型，
# 但 LiteLLM 期望 OpenAI 格式，所以需要来回转换。
# 如果直接用 LangChain 的 ChatModel（如 ChatOpenAI），则不需要转换。
def agent_node(state: MessagesState) -> dict:
    """Agent 推理节点"""
    from litellm import completion

    # 构造消息：系统提示 + 历史 + 当前
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    # 裁剪过长历史（保留最近 20 条）
    if len(messages) > 22:  # 1 system + 20 history + 1 current
        messages = [messages[0]] + messages[-21:]

    # 将 LangChain 消息转为 LiteLLM/OpenAI 格式
    # 注意：LangChain 的 .type 返回 "human"/"ai"/"system"/"tool"
    # 而 LiteLLM/OpenAI 期望 "user"/"assistant"/"system"/"tool"
    role_map = {"human": "user", "ai": "assistant", "system": "system", "tool": "tool"}

    litellm_messages = []
    for m in messages:
        role = role_map.get(m.type, "user")
        if m.type == "tool":
            # ToolMessage 必须携带 tool_call_id 和 content
            litellm_messages.append({
                "role": "tool",
                "content": m.content or "",
                "tool_call_id": getattr(m, "tool_call_id", ""),
            })
        else:
            litellm_messages.append({
                "role": role,
                "content": m.content or "",
            })

    # 调用 LLM
    response = completion(
        model=os.getenv("LLM_PROVIDER", "deepseek") + "/" + os.getenv("LLM_MODEL", "deepseek-chat"),
        messages=litellm_messages,
        tools=[{"type": "function", "function": t.args} for t in ALL_TOOLS],
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        api_key=os.getenv("LLM_API_KEY"),
        api_base=os.getenv("LLM_API_BASE"),
    )

    ai_message = response.choices[0].message

    # 将 LiteLLM 的 tool_calls 从 OpenAI 格式转为 LangChain 格式
    # OpenAI: {"function": {"name": ..., "arguments": ...}, "id": ...}
    # LangChain: {"name": ..., "arguments": ..., "id": ...}
    lc_tool_calls = []
    for tc in (ai_message.tool_calls or []):
        lc_tool_calls.append({
            "name": tc.function.name,
            "arguments": tc.function.arguments,
            "id": tc.id,
        })

    msg = AIMessage(
        content=ai_message.content or "",
        tool_calls=lc_tool_calls if lc_tool_calls else None,
    )

    return {"messages": [msg]}

# ============================================
# 4. 构建图
# ============================================
# 图的结构非常经典：START → agent → (条件路由) → tools → agent → ...
# agent 节点根据 tools_condition 的判断结果决定走向：
#   - 有 tool_calls → 进入 tools 节点执行工具
#   - 无 tool_calls → 到达 END，返回结果
# tools 节点执行完后固定回到 agent，形成循环。
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(ALL_TOOLS))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

# ============================================
# 5. 编译（带持久化 + 递归限制）
# ============================================
# InMemorySaver 提供内存级别的状态持久化，支持多轮对话。
# recursion_limit=10 防止 Agent 和 Tools 之间无限循环。
# 生产环境应替换为 SqliteSaver 或 PostgresSaver。
checkpointer = InMemorySaver()
app = builder.compile(
    checkpointer=checkpointer,
    recursion_limit=10  # 防止无限循环
)

# ============================================
# 6. 运行
# ============================================
# chat() 函数封装了 invoke 调用，自动管理 thread_id。
# 同一个 thread_id 下的多次调用会共享对话历史（由 Checkpointer 管理）。
# 底部的测试代码演示了三轮对话：工具调用、时间查询、上下文回忆。
def chat(message: str, thread_id: str = None) -> str:
    """简单的对话接口"""
    if not thread_id:
        thread_id = str(uuid.uuid4())

    config = {"configurable": {"thread_id": thread_id}}

    result = app.invoke(
        {"messages": [HumanMessage(content=message)]},
        config=config
    )

    return result["messages"][-1].content, thread_id

# 测试
if __name__ == "__main__":
    tid = "test_session"

    answer, tid = chat("Python 是谁创建的？", tid)
    print(f"Q: Python 是谁创建的？\nA: {answer}\n")

    answer, tid = chat("现在几点了？", tid)
    print(f"Q: 现在几点了？\nA: {answer}\n")

    answer, tid = chat("刚才我问了什么？", tid)
    print(f"Q: 刚才我问了什么？\nA: {answer}\n")
```

---

## 关键设计决策总结

下面的表格总结了实现中的每个重要选择及其背后的原因。这些决策不是唯一的方案，但对于一个标准 RAG Agent 来说是经过验证的最佳实践。

| 决策 | 选择 | 原因 |
|------|------|------|
| State 类型 | `MessagesState` | 标准 Agent 模式，自动消息追加 |
| 工具节点 | 预置 `ToolNode` | 自动处理 tool_calls → ToolMessage 转换 |
| 条件路由 | `tools_condition` | 标准 Agent 模式的默认路由 |
| 持久化 | `InMemorySaver` | 开发阶段用内存，生产换 SQLite |
| 递归限制 | 10 | 防止 Agent-Tools 无限循环 |
| 消息裁剪 | 最近 20 条 | 控制 Token 消耗 |
