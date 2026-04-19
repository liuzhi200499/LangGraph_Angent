from langchain_core.messages import SystemMessage, HumanMessage
from litellm import completion
from config.settings import settings
from core.prompts import SYSTEM_PROMPT
from tools.search_tool import search_knowledge_base
from tools.calculator_tool import calculate
from tools.time_tool import get_current_time

ALL_TOOLS = [search_knowledge_base, get_current_time, calculate]


def agent_node(state: dict) -> dict:
    """Agent 推理节点：调用 LLM 并处理工具调用"""
    messages = state["messages"]
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + list(messages)

    tool_schemas = []
    for t in ALL_TOOLS:
        schema = t.get_function_schema()
        tool_schemas.append(schema)

    response = completion(
        model=f"{settings.LLM_PROVIDER}/{settings.LLM_MODEL}",
        messages=[{"role": m.type, "content": m.content} if not hasattr(m, "tool_calls") else {"role": "assistant", "content": m.content or "", "tool_calls": m.tool_calls} for m in full_messages],
        tools=tool_schemas if tool_schemas else None,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.LLM_MAX_TOKENS,
        api_key=settings.LLM_API_KEY,
        api_base=settings.LLM_API_BASE,
    )

    ai_message = response.choices[0].message
    return {"messages": [ai_message]}
