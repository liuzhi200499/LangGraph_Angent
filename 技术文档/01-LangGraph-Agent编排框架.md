# LangGraph — Agent 编排框架技术文档

---

## 1. 技术概述

LangGraph 是 LangChain 团队推出的低级 Agent 编排框架，专注于构建**有状态、可靠、可扩展**的多步骤 AI 工作流。它将 Agent 执行流程建模为**有向图（Directed Graph）**，通过节点（Node）、边（Edge）、状态（State）三个核心概念实现复杂逻辑的清晰表达。

| 项目 | 说明 |
|------|------|
| 版本 | v1.1（2026 年 3 月） |
| 语言 | Python |
| 官方文档 | https://langchain-ai.github.io/langgraph/ |
| 安装 | `pip install langgraph==0.2.0` |
| 定位 | 低级框架，聚焦 Agent 编排，不提供高层抽象 |

---

## 2. 核心概念

### 2.1 三个基本要素

```
┌───────────────────────────────────────────────┐
│                  State（状态）                 │
│         节点间传递的共享数据结构                 │
│                                               │
│   ┌─────────┐    Edge    ┌─────────┐          │
│   │  Node   │ ──────────►│  Node   │          │
│   │ (节点)  │◄──────────│ (节点)  │          │
│   └─────────┘    Edge    └─────────┘          │
│                                               │
│   Node = 编码 Agent 逻辑的 Python 函数          │
│   Edge = 决定下一个执行哪个节点的规则             │
└───────────────────────────────────────────────┘
```

**Node（节点）**
- 就是一个普通的 Python 函数（同步或异步）
- 接收当前 State，返回更新后的 State
- 代表一个执行步骤：调用 LLM、执行工具、数据处理等

**Edge（边）**
- 决定执行完一个节点后，下一个执行哪个节点
- 分为固定边（无条件跳转）和条件边（根据状态动态路由）

**State（状态）**
- 所有节点共享的数据结构
- 通过 `TypedDict` 或 Pydantic Model 定义
- 每个节点读取并更新 State

### 2.2 Super-step 执行模型

LangGraph 采用类似 Google Pregel 的并行执行模型：

```
Super-step 1:  [Node A] [Node B] [Node C]   ← 并行执行
                    │       │       │
Super-step 2:  [Node D] [Node E]             ← 依赖上一步结果
                    │       │
Super-step 3:  [Node F]                     ← 最终汇总
```

同一 super-step 内的节点并行执行，跨 super-step 的节点串行执行。

---

## 3. 安装与环境准备

### 3.1 安装

```bash
pip install langgraph==0.2.0
# LangGraph 依赖 langchain-core，会自动安装
```

### 3.2 验证安装

```python
import langgraph
print(langgraph.__version__)  # 应输出 0.2.0
```

---

## 4. 快速开始：构建第一个 Agent

### 4.1 最简单的图

```python
from langgraph.graph import StateGraph, MessagesState, START, END

# 定义节点函数
def greet(state: MessagesState):
    """简单问候节点"""
    return {"messages": [{"role": "ai", "content": "你好！我是 LangGraph Agent。"}]}

# 构建图
graph = StateGraph(MessagesState)
graph.add_node("greet", greet)
graph.add_edge(START, "greet")   # 入口 → greet
graph.add_edge("greet", END)     # greet → 出口

# 编译并运行
app = graph.compile()
result = app.invoke({"messages": [{"role": "user", "content": "你好"}]})
print(result["messages"][-1]["content"])
# 输出：你好！我是 LangGraph Agent。
```

### 4.2 执行流程

```
START → greet 节点（执行 greet 函数） → END
```

---

## 5. 完整使用流程

### 5.1 第一步：定义状态

State 是图中所有节点共享的数据。最常用的是 `MessagesState`（消息列表）：

```python
from langgraph.graph import MessagesState

# MessagesState 内部结构等价于：
# class MessagesState(TypedDict):
#     messages: Annotated[list[BaseMessage], add_messages]
```

也可以自定义 State：

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class MyState(TypedDict):
    messages: Annotated[list, add_messages]  # 消息列表（自动追加）
    context: str                              # 自定义字段
    tool_results: list                        # 工具执行结果
```

**`add_messages` 的作用：** 当节点返回 `{"messages": [new_msg]}` 时，新消息会自动追加到已有列表，而非覆盖。

### 5.2 第二步：定义节点

节点就是接收 State 并返回 State 更新的函数：

```python
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

def agent_node(state: MessagesState):
    """Agent 推理节点：调用 LLM 决定下一步"""
    messages = state["messages"]

    # 调用 LLM
    response = call_your_llm(messages)

    # 返回更新（会自动追加到 messages 列表）
    return {"messages": [response]}

def tools_node(state: MessagesState):
    """工具执行节点：执行 Agent 选择的工具"""
    last_message = state["messages"][-1]

    # 提取工具调用并执行
    results = []
    for tool_call in last_message.tool_calls:
        result = execute_tool(tool_call)
        results.append(result)

    return {"messages": results}
```

### 5.3 第三步：构建图

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

# 创建图构建器
builder = StateGraph(MessagesState)

# 添加节点
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode([search_tool, calc_tool]))  # 使用预置 ToolNode

# 添加边
builder.add_edge(START, "agent")                          # 入口 → agent
builder.add_conditional_edges("agent", tools_condition)   # agent → 条件路由
builder.add_edge("tools", "agent")                        # tools → agent（循环回去）

# 条件路由 tools_condition 的逻辑：
# 如果 agent 返回了 tool_calls → 路由到 "tools" 节点
# 如果 agent 直接返回了文本 → 路由到 END（结束）
```

**边的类型总结：**

| 边类型 | 方法 | 说明 |
|--------|------|------|
| 固定边 | `add_edge(from, to)` | 无条件跳转 |
| 条件边 | `add_conditional_edges(from, router)` | 根据状态动态路由 |
| 入口边 | `add_edge(START, node)` | 程序入口连接第一个节点 |
| 出口边 | `add_edge(node, END)` | 节点连接程序出口 |

### 5.4 第四步：编译图

```python
# 不带持久化（简单模式）
app = builder.compile()

# 带持久化（支持多轮对话）
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)
```

### 5.5 第五步：运行图

```python
from langchain_core.messages import HumanMessage

# === 同步调用 ===
result = app.invoke(
    {"messages": [HumanMessage(content="什么是机器学习？")]},
    config={"configurable": {"thread_id": "session_001"}}
)
print(result["messages"][-1].content)

# === 流式输出 ===
for chunk in app.stream(
    {"messages": [HumanMessage(content="解释深度学习")]},
    config={"configurable": {"thread_id": "session_001"}}
):
    print(chunk)  # 每个节点的输出实时返回

# === 异步调用 ===
result = await app.ainvoke(
    {"messages": [HumanMessage(content="你好")]},
    config={"configurable": {"thread_id": "session_001"}}
)

# === 异步流式 ===
async for chunk in app.astream(
    {"messages": [HumanMessage(content="你好")]},
    config={"configurable": {"thread_id": "session_001"}}
):
    print(chunk)
```

---

## 6. 进阶用法

### 6.1 工具集成（ToolNode）

LangGraph 提供预置的 `ToolNode`，自动处理工具调用：

```python
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode

# 定义工具
@tool
def search_knowledge(query: str) -> str:
    """搜索知识库"""
    return f"搜索结果：{query} 的相关内容..."

@tool
def calculate(expression: str) -> str:
    """执行数学计算"""
    return str(eval(expression))

# 创建 ToolNode
tools = [search_knowledge, calculate]
tool_node = ToolNode(tools)

# 添加到图
builder.add_node("tools", tool_node)
```

`ToolNode` 的工作原理：
1. 接收上一条消息中的 `tool_calls`
2. 根据 `name` 字段匹配对应的工具函数
3. 执行工具并返回 `ToolMessage`

### 6.2 条件路由

`tools_condition` 是最常用的路由函数，也可以自定义：

```python
def custom_router(state: MessagesState) -> str:
    """自定义路由逻辑"""
    last_message = state["messages"][-1]

    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"           # 需要调用工具
    elif "转人工" in last_message.content:
        return "human_handoff"   # 转人工
    else:
        return END               # 直接结束

builder.add_conditional_edges("agent", custom_router)
```

### 6.3 持久化与多轮对话

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)

# 第一轮
r1 = app.invoke(
    {"messages": [HumanMessage(content="我叫张三")]},
    config={"configurable": {"thread_id": "user_001"}}
)

# 第二轮（同一 thread_id，Agent 记得上一轮内容）
r2 = app.invoke(
    {"messages": [HumanMessage(content="我叫什么名字？")]},
    config={"configurable": {"thread_id": "user_001"}}
)
# Agent 会回答 "张三"
```

**不同 thread_id 完全隔离：**

```python
# 用户 A 的对话
app.invoke({"messages": [...]}, config={"configurable": {"thread_id": "A"}})

# 用户 B 的对话（互不影响）
app.invoke({"messages": [...]}, config={"configurable": {"thread_id": "B"}})
```

### 6.4 Human-in-the-Loop（人机协作）

可以在执行流程中暂停，等待人工审批：

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()

# 在编译时指定中断点
app = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"]  # 在执行 tools 节点前暂停
)

# 第一次调用：执行到 tools 前暂停
result = app.invoke(
    {"messages": [HumanMessage(content="删除所有数据")]},
    config={"configurable": {"thread_id": "review_001"}}
)

# 人工审查后决定是否继续
# 获取待审批的工具调用
pending_tool_calls = result["messages"][-1].tool_calls
print(f"Agent 想执行: {pending_tool_calls}")

# 确认后继续执行
result = app.invoke(
    None,  # 传 None 表示继续之前暂停的执行
    config={"configurable": {"thread_id": "review_001"}}
)
```

### 6.5 子图（Subgraph）

将复杂工作流拆分为可复用的子图：

```python
# 定义子图：知识检索子流程
def build_retrieval_subgraph():
    sub = StateGraph(MessagesState)
    sub.add_node("search", search_node)
    sub.add_node("rank", rank_node)
    sub.add_edge(START, "search")
    sub.add_edge("search", "rank")
    sub.add_edge("rank", END)
    return sub.compile()

# 在主图中使用子图
builder.add_node("retrieval", build_retrieval_subgraph())
builder.add_edge("agent", "retrieval")
builder.add_edge("retrieval", "response")
```

### 6.6 Time Travel 调试

回放历史执行状态，用于调试：

```python
# 获取所有历史状态
states = list(app.get_state_history(
    config={"configurable": {"thread_id": "user_001"}}
))

# 回放某个历史状态
for state in states:
    print(f"Step {state.metadata['step']}: {state.values}")

# 从某个历史节点重新执行
app.invoke(
    None,
    config={"configurable": {"thread_id": "user_001"}},
    checkpoint_id=states[2].config["configurable"]["checkpoint_id"]
)
```

---

## 7. 完整示例：RAG Agent

以下是一个完整的 RAG（检索增强生成）Agent 实现：

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_core.messages import HumanMessage, SystemMessage

# === 工具定义 ===
@tool
def search_knowledge(query: str) -> str:
    """在知识库中搜索相关信息"""
    # 实际项目中调用 MenteeDB
    mock_results = [
        "Python 是由 Guido van Rossum 于 1991 年创建的编程语言。",
        "Python 广泛应用于 Web 开发、数据科学、AI 等领域。"
    ]
    return "\n".join(mock_results)

@tool
def get_current_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

ALL_TOOLS = [search_knowledge, get_current_time]

# === 系统提示 ===
SYSTEM_PROMPT = """你是一个智能知识库助手。
你可以使用工具搜索知识库或获取时间信息。
请根据用户问题决定是否需要调用工具。"""

# === Agent 节点 ===
def agent_node(state: MessagesState):
    from litellm import completion
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = completion(
        model="deepseek/deepseek-chat",
        messages=[m.dict() for m in messages],
        tools=[t.get_function_schema() for t in ALL_TOOLS],
        api_key="your-key",
    )
    ai_msg = response.choices[0].message
    return {"messages": [ai_msg]}

# === 构建图 ===
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(ALL_TOOLS))
builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

# === 编译 ===
checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)

# === 运行 ===
# 第一轮
r1 = app.invoke(
    {"messages": [HumanMessage(content="Python 是谁创建的？")]},
    config={"configurable": {"thread_id": "demo"}}
)
print(r1["messages"][-1].content)

# 第二轮
r2 = app.invoke(
    {"messages": [HumanMessage(content="现在几点了？")]},
    config={"configurable": {"thread_id": "demo"}}
)
print(r2["messages"][-1].content)
```

**执行流程图：**

```
用户："Python 是谁创建的？"
  │
  ▼
START → agent → (检测到需要工具) → tools → agent → END
         │                                    │
         │ 调用 LLM                           │ 再次调用 LLM
         │ 决定使用 search_knowledge           │ 基于工具结果生成回答
         │                                    │
         └────────────────────────────────────┘
```

---

## 8. 常见问题与最佳实践

### 8.1 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 图无限循环 | 工具结果未正确返回 | 确保工具返回 `ToolMessage` |
| 状态丢失 | 未使用 Checkpointer | 添加 `MemorySaver` 并配置 `thread_id` |
| 工具不被调用 | Prompt 未明确引导 | 在系统提示中说明何时使用工具 |
| 内存持续增长 | 历史消息无限累积 | 定期清理或限制消息数量 |

### 8.2 最佳实践

1. **保持节点函数纯粹** — 节点只负责接收 State、处理逻辑、返回更新
2. **使用 `tools_condition`** — 对于标准 Agent 模式，使用预置条件路由
3. **始终配置 Checkpointer** — 生产环境必须持久化对话状态
4. **控制上下文长度** — 在 agent 节点中裁剪历史消息，避免 Token 超限
5. **错误处理** — 在节点中添加 try-catch，返回错误消息而非抛异常
