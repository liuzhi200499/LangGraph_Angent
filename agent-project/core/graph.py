"""
LangGraph 图构建模块
定义 Agent 的工作流图结构，实现 ReAct（Reason-Act）模式：
Agent 思考 → 判断是否需要工具 → 执行工具 → 回到 Agent 继续思考 → 最终回答

图结构：
  START → agent ──(条件边)──→ tools → agent（循环）
                   └──(无需工具)──→ END
"""
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from core.agent import agent_node, ALL_TOOLS


def build_agent_graph():
    """
    构建 LangGraph Agent 工作流图

    节点:
    - agent: 调用 LLM 进行推理决策
    - tools: 执行 Agent 选择的工具调用

    边:
    - START → agent: 入口固定指向 Agent 节点
    - agent → (条件路由): 根据 tools_condition 判断：
        · LLM 返回 tool_calls → 路由到 tools 节点
        · LLM 无 tool_calls → 路由到 END，对话结束
    - tools → agent: 工具执行完毕后，结果返回 Agent 继续推理

    持久化:
    - 使用 InMemorySaver 保存对话状态，支持多会话隔离（通过 thread_id）
    """
    # 使用 MessagesState 作为共享状态，自动管理消息列表的追加
    builder = StateGraph(MessagesState)

    # 添加两个核心节点
    builder.add_node("agent", agent_node)              # LLM 推理节点
    builder.add_node("tools", ToolNode(ALL_TOOLS))     # 工具执行节点（LangGraph 内置）

    # 定义执行流
    builder.add_edge(START, "agent")                          # 入口 → Agent
    builder.add_conditional_edges("agent", tools_condition)   # Agent → 条件路由（工具或结束）
    builder.add_edge("tools", "agent")                        # Tools → Agent（循环回推理节点）

    # 编译图并添加 InMemorySaver 持久化，支持多轮对话状态保持
    checkpointer = InMemorySaver()
    return builder.compile(checkpointer=checkpointer)
