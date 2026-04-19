"""
Agent 推理节点模块
核心模块：负责调用 LLM 进行推理决策，判断是否需要调用工具。
通过 LiteLLM 统一接口支持 100+ 模型，实现模型无缝切换。
"""
import json
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from litellm import completion
from config.settings import settings
from core.prompts import SYSTEM_PROMPT
from tools.search_tool import search_knowledge_base
from tools.calculator_tool import calculate
from tools.time_tool import get_current_time

# Agent 可调用的所有工具列表，ToolNode 会使用此列表进行工具执行
ALL_TOOLS = [search_knowledge_base, get_current_time, calculate]


def agent_node(state: dict) -> dict:
    """
    Agent 推理节点（LangGraph Node）
    接收当前对话状态，调用 LLM 决定下一步操作：
    - 直接回复用户
    - 调用某个工具获取信息后再回复

    参数:
        state: LangGraph 状态字典，包含 "messages" 键（消息列表）
    返回:
        包含新消息的状态更新字典，将被合并到图状态中
    """
    messages = state["messages"]

    # 在用户消息前插入系统提示词，定义 Agent 的行为规范
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    # 将所有工具转换为 LLM 可识别的 function calling schema
    tool_schemas = []
    for t in ALL_TOOLS:
        schema = {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.get_input_jsonschema(),
            },
        }
        tool_schemas.append(schema)

    # LangChain message type → OpenAI role 映射
    role_map = {"system": "system", "human": "user", "ai": "assistant", "tool": "tool"}

    def to_openai_msg(m):
        if hasattr(m, "tool_calls") and m.tool_calls:
            openai_tcs = []
            for tc in m.tool_calls:
                openai_tcs.append({
                    "type": "function",
                    "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
                    "id": tc.get("id", ""),
                })
            return {"role": "assistant", "content": m.content or "", "tool_calls": openai_tcs}
        if m.type == "tool":
            return {"role": "tool", "content": m.content, "tool_call_id": getattr(m, "tool_call_id", "")}
        return {"role": role_map.get(m.type, m.type), "content": m.content}

    # 通过 LiteLLM 调用 LLM，model 格式为 "provider/model"
    response = completion(
        model=f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
        messages=[to_openai_msg(m) for m in full_messages],
        tools=tool_schemas if tool_schemas else None,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
        timeout=120,
    )

    # 将 LiteLLM/OpenAI 的响应转换为 LangChain AIMessage
    raw = response.choices[0].message
    ai_message = AIMessage(content=raw.content or "")
    if raw.tool_calls:
        ai_message.tool_calls = [
            {
                "name": tc.function.name,
                "args": json.loads(tc.function.arguments),
                "id": tc.id or "",
                "type": "tool_call",
            }
            for tc in raw.tool_calls
        ]
    return {"messages": [ai_message]}
