# LangGraph — Agent 编排框架技术文档（深度拆解版）

---

## 目录

- [1. 技术概述](#1-技术概述)
- [2. 安装与环境](#2-安装与环境)
- [3. 难点一：State 状态机制完全解析](#3-难点一state-状态机制完全解析)
- [4. 难点二：Node 节点内部运作](#4-难点二node-节点内部运作)
- [5. 难点三：Edge 边与条件路由](#5-难点三edge-边与条件路由)
- [6. 难点四：ToolNode 工具节点全链路](#6-难点四toolnode-工具节点全链路)
- [7. 难点五：消息流转全链路追踪](#7-难点五消息流转全链路追踪)
- [8. 难点六：Checkpointer 持久化原理](#8-难点六checkpointer-持久化原理)
- [9. 难点七：Human-in-the-Loop 完整流程](#9-难点七human-in-the-loop-完整流程)
- [10. 难点八：编译与运行时行为](#10-难点八编译与运行时行为)
- [11. 难点九：图的无限循环防护](#11-难点九图的无限循环防护)
- [12. 难点十：多 Agent 协作模式](#12-难点十多-agent-协作模式)
- [13. 难点十一：错误处理与重试策略](#13-难点十一错误处理与重试策略)
- [14. 难点十二：调试与问题排查](#14-难点十二调试与问题排查)
- [15. 完整实战：从零构建 RAG Agent](#15-完整实战从零构建-rag-agent)

---

## 1. 技术概述

LangGraph 是 LangChain 团队推出的低级 Agent 编排框架。核心思想：**把 Agent 的执行过程建模为一张有向图**。

| 项目 | 说明 |
|------|------|
| 版本 | v1.1（2026 年 3 月） |
| 语言 | Python |
| 官方文档 | https://langchain-ai.github.io/langgraph/ |
| 安装 | `pip install langgraph==0.2.0` |
| 一句话理解 | 用 Python 函数当节点、用条件判断当连线，画出 Agent 的执行流程图 |

**LangGraph 和 LangChain 的关系：**

```
LangChain（高层框架）
  ├── 提供工具定义、消息类型、LLM 调用接口
  └── 不关心执行流程怎么编排

LangGraph（低层框架）
  ├── 依赖 LangChain 的消息和工具类型
  └── 专注于：谁先执行、谁后执行、什么条件跳转
```

---

## 2. 安装与环境

```bash
pip install langgraph==0.2.0
# 自动安装 langchain-core、langgraph-checkpoint 等依赖

# 验证
python -c "import langgraph; print(langgraph.__version__)"
```

---

## 3. 难点一：State 状态机制完全解析

### 3.1 State 是什么

State 是图中**所有节点共享的、唯一的数据容器**。可以理解为一个全局字典，每个节点都能读它、改它。

```
                    State = { messages: [...], context: "..." }
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
     Node A 读取 State        Node B 读取 State        Node C 读取 State
     Node A 返回更新          Node B 返回更新           Node C 返回更新
          │                       │                       │
          └───────────────────────┼───────────────────────┘
                                  │
                    State 被更新，传给下一批节点
```

### 3.2 最常用的内置 State：MessagesState

```python
from langgraph.graph import MessagesState

# MessagesState 等价于：
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class MessagesState(TypedDict):
    messages: Annotated[list, add_messages]
```

**拆解这个定义的每个部分：**

| 部分 | 含义 |
|------|------|
| `TypedDict` | 声明这是一个有固定 key 的字典类型 |
| `messages: list` | messages 字段是一个列表 |
| `Annotated[list, add_messages]` | 关键！给这个列表附加了一个 **Reducer 函数** `add_messages` |

### 3.3 Reducer 函数：State 更新的核心机制

**没有 Reducer 时（默认行为 = 覆盖）：**

```python
class SimpleState(TypedDict):
    counter: int

# 如果 State = {"counter": 5}
# 节点返回 {"counter": 10}
# 结果：State = {"counter": 10}  ← 直接覆盖
```

**有 Reducer 时（add_messages = 追加合并）：**

```python
class MessagesState(TypedDict):
    messages: Annotated[list, add_messages]

# 如果 State = {"messages": [msg1, msg2]}
# 节点返回 {"messages": [msg3]}
# 结果：State = {"messages": [msg1, msg2, msg3]}  ← 追加而非覆盖
```

**`add_messages` 的智能行为：**

```python
# 行为 1：新消息追加到列表
旧状态: [HumanMessage("你好")]
节点返回: [AIMessage("你好！")]
结果: [HumanMessage("你好"), AIMessage("你好！")]

# 行为 2：相同 ID 的消息会被替换（更新而非重复）
旧状态: [AIMessage("思考中...", id="msg_1")]
节点返回: [AIMessage("最终回答", id="msg_1")]  # 同一 ID
结果: [AIMessage("最终回答", id="msg_1")]      # 替换了旧内容

# 行为 3：可以同时追加多条
旧状态: [HumanMessage("你好")]
节点返回: [AIMessage("你好"), ToolMessage(...)]
结果: [HumanMessage("你好"), AIMessage("你好"), ToolMessage(...)]
```

### 3.4 自定义 State（多字段 + 不同 Reducer）

```python
from typing import TypedDict, Annotated
from operator import add

def merge_dicts(old: dict, new: dict) -> dict:
    """自定义 Reducer：合并字典"""
    merged = {**old, **new}
    return merged

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]  # 追加消息
    context: str                             # 覆盖（默认行为）
    scores: Annotated[list, add]             # 列表拼接（operator.add）
    metadata: Annotated[dict, merge_dicts]   # 字典合并
```

**各字段的行为差异：**

```python
# 假设当前 State：
state = {
    "messages": [HumanMessage("你好")],
    "context": "初始上下文",
    "scores": [0.8],
    "metadata": {"user": "张三"}
}

# 节点返回：
update = {
    "messages": [AIMessage("你好！")],
    "context": "新的上下文",           # 覆盖
    "scores": [0.9, 0.7],             # 拼接
    "metadata": {"page": 2}           # 合并
}

# 最终 State：
{
    "messages": [HumanMessage("你好"), AIMessage("你好！")],  # add_messages
    "context": "新的上下文",                                    # 覆盖
    "scores": [0.8, 0.9, 0.7],                                # operator.add 拼接
    "metadata": {"user": "张三", "page": 2}                    # merge_dicts 合并
}
```

### 3.5 State 的生命周期

```
invoke() 调用
  │
  ▼
创建初始 State = 你传入的 input
  │
  ▼
Node A 执行 ─── 读取 State ─── 返回更新 ─── State 被合并更新
  │
  ▼
Router 判断 ─── 读取 State ─── 决定下一个节点
  │
  ▼
Node B 执行 ─── 读取 State ─── 返回更新 ─── State 被合并更新
  │
  ▼
到达 END ─── 返回最终 State 给调用者
```

---

## 4. 难点二：Node 节点内部运作

### 4.1 节点到底是什么

节点就是一个 **Python 函数**，签名为：

```python
def my_node(state: StateType) -> dict:
    #   ↑ 接收当前 State
    #                      ↑ 返回 State 的部分更新（不是完整 State）
    return {"key_to_update": new_value}
```

**关键理解：**
- 节点**不需要**返回完整的 State，只返回需要更新的字段
- 未提及的字段**保持不变**
- 返回值会通过 Reducer 合并到 State 中

### 4.2 节点的完整生命周期

```python
def agent_node(state: MessagesState) -> dict:
    # ===== 阶段 1：读取 State =====
    messages = state["messages"]   # 获取所有历史消息

    # ===== 阶段 2：执行业务逻辑 =====
    # 调用 LLM、执行计算、访问数据库...
    response = call_llm(messages)

    # ===== 阶段 3：返回更新 =====
    # 只返回需要更新的字段
    return {"messages": [response]}
    # LangGraph 自动用 add_messages 合并到 State
```

### 4.3 节点可以返回空更新

```python
def log_node(state: MessagesState) -> dict:
    """只做日志记录，不修改 State"""
    print(f"当前消息数: {len(state['messages'])}")
    return {}  # 空字典 = 不更新任何字段
```

### 4.4 同步节点 vs 异步节点

```python
# 同步节点
def sync_node(state: MessagesState) -> dict:
    result = requests.post(...)  # 同步 HTTP 请求
    return {"messages": [AIMessage(content=result.text)]}

# 异步节点（推荐用于 I/O 密集型操作）
async def async_node(state: MessagesState) -> dict:
    result = await aiohttp.post(...)  # 异步 HTTP 请求
    return {"messages": [AIMessage(content=result.text)]}

# 两种都可以添加到图中，LangGraph 自动识别
builder.add_node("sync", sync_node)
builder.add_node("async", async_node)
```

---

## 5. 难点三：Edge 边与条件路由

### 5.1 固定边：无条件跳转

```python
builder.add_edge(START, "agent")   # 入口 → 永远先执行 agent
builder.add_edge("tools", "agent")  # tools 执行完 → 永远回到 agent
builder.add_edge("respond", END)    # respond 执行完 → 结束
```

**固定边 = 写死的箭头，不看任何条件。**

### 5.2 条件边：根据 State 动态路由

```python
builder.add_conditional_edges(
    "agent",          # 从哪个节点出发
    router_function,  # 路由函数：接收 State，返回目标节点名
)
```

**路由函数的签名：**

```python
def router_function(state: StateType) -> str:
    # 读取 State，决定下一个节点
    # 返回值必须是：节点名（str）或 END
    ...
```

### 5.3 内置路由函数：tools_condition

LangGraph 预置了 `tools_condition`，这是最常用的路由函数。理解它的内部逻辑非常重要：

```python
from langgraph.prebuilt import tools_condition

# tools_condition 的内部逻辑等价于：
def tools_condition(state: MessagesState) -> str:
    last_message = state["messages"][-1]

    # 检查最后一条消息是否有 tool_calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        return "tools"   # 有工具调用 → 去工具节点
    else:
        return END       # 没有 → 直接结束
```

**什么时候 last_message 会有 `tool_calls`？**

```
LLM 返回的 AIMessage 有两种情况：

情况 1：LLM 决定直接回答
  AIMessage(content="你好！我是AI助手。", tool_calls=[])
  → tools_condition 返回 END → 对话结束

情况 2：LLM 决定调用工具
  AIMessage(content="", tool_calls=[
      {"name": "search_knowledge", "arguments": {"query": "Python"}}
  ])
  → tools_condition 返回 "tools" → 进入工具节点
```

### 5.4 自定义多路分支路由

```python
def smart_router(state: MessagesState) -> str:
    """多路分支：根据内容决定去哪个节点"""
    last_msg = state["messages"][-1]

    # 分支 1：需要工具
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        return "tools"

    # 分支 2：转人工
    if last_msg.content and "转人工" in last_msg.content:
        return "human_handoff"

    # 分支 3：需要审核
    if last_msg.content and len(last_msg.content) > 1000:
        return "review"

    # 分支 4：直接结束
    return END

# 使用时需要指定所有可能的目标节点
builder.add_conditional_edges(
    "agent",
    smart_router,
    {"tools": "tools", "human_handoff": "human_node", "review": "review_node", END: END}
)
```

### 5.5 边连接的常见错误

```python
# ❌ 错误：忘记添加 tools → agent 的回路边
# 会导致工具执行完就报错（没有下一条边）
builder.add_edge("tools", END)  # 工具结果不会回到 Agent

# ✅ 正确：形成 Agent ↔ Tools 循环
builder.add_edge("tools", "agent")  # 工具执行完回到 Agent 继续推理

# ❌ 错误：路由函数返回了不存在的节点名
def bad_router(state):
    return "nonexistent_node"  # 会报 KeyError

# ✅ 正确：确保返回的每个节点名都已通过 add_node 注册
```

---

## 6. 难点四：ToolNode 工具节点全链路

### 6.1 @tool 装饰器：从函数到工具

```python
from langchain_core.tools import tool
from pydantic import BaseModel, Field

# 方式 1：简单定义（自动从函数签名推断参数）
@tool
def get_time() -> str:
    """获取当前时间"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# 方式 2：带 Schema 定义（推荐，描述更精确）
class SearchInput(BaseModel):
    query: str = Field(description="搜索关键词")
    top_k: int = Field(default=5, description="返回结果数量")

@tool(args_schema=SearchInput)
def search_knowledge(query: str, top_k: int = 5) -> str:
    """在知识库中搜索相关信息"""
    results = vector_db.search(query, top_k)
    return format_results(results)
```

**`@tool` 做了什么？**

```python
# 普通 Python 函数
def search(query: str) -> str:
    ...

# @tool 包装后变成了 Tool 对象，包含：
# 1. name: "search_knowledge"          ← 函数名
# 2. description: "在知识库中搜索..."    ← docstring
# 3. args_schema: SearchInput          ← 参数 Schema
# 4. 函数体本身（调用时执行）

# Tool 可以生成 LLM 能理解的 Function Calling Schema：
schema = search_knowledge.get_function_schema()
# {
#   "name": "search_knowledge",
#   "description": "在知识库中搜索相关信息",
#   "parameters": {
#     "type": "object",
#     "properties": {
#       "query": {"type": "string", "description": "搜索关键词"},
#       "top_k": {"type": "integer", "description": "返回结果数量", "default": 5}
#     },
#     "required": ["query"]
#   }
# }
```

### 6.2 ToolNode 的内部工作机制

```
Agent 节点返回 AIMessage（带 tool_calls）
  │
  ▼
ToolNode 接收 State
  │
  ├── 1. 从 messages[-1] 提取 tool_calls 列表
  │
  │   tool_calls = [
  │       {"name": "search_knowledge", "arguments": {"query": "Python"}, "id": "call_abc"},
  │       {"name": "get_time", "arguments": {}, "id": "call_def"}
  │   ]
  │
  ├── 2. 遍历每个 tool_call，按 name 匹配工具函数
  │
  │   "search_knowledge" → 调用 search_knowledge(query="Python") → "搜索结果..."
  │   "get_time"         → 调用 get_time()                       → "2026-04-19 15:30"
  │
  ├── 3. 将每个结果包装为 ToolMessage
  │
  │   ToolMessage(content="搜索结果...", tool_call_id="call_abc")
  │   ToolMessage(content="2026-04-19 15:30", tool_call_id="call_abc")
  │
  └── 4. 返回 {"messages": [ToolMessage1, ToolMessage2]}

State 中的 messages 变为：
[HumanMessage, AIMessage(tool_calls), ToolMessage(result1), ToolMessage(result2)]
```

### 6.3 tool_call_id：连接请求和响应的关键

```python
# LLM 返回的 AIMessage 中每个 tool_call 都有唯一 ID
ai_msg = AIMessage(
    content="",
    tool_calls=[
        {"name": "search", "arguments": {"query": "Python"}, "id": "call_001"},
        {"name": "search", "arguments": {"query": "AI"},     "id": "call_002"},
    ]
)

# ToolNode 返回的 ToolMessage 必须匹配对应 ID
tool_msg_1 = ToolMessage(content="Python结果...", tool_call_id="call_001")
tool_msg_2 = ToolMessage(content="AI结果...",     tool_call_id="call_002")

# 这样 Agent 节点再次调用 LLM 时，LLM 能把每个工具结果对应到正确的请求
```

### 6.4 手动实现 ToolNode（理解原理）

```python
from langchain_core.messages import ToolMessage

def custom_tool_node(state: MessagesState) -> dict:
    """手动实现的 ToolNode，理解内部逻辑"""
    last_msg = state["messages"][-1]
    tool_calls = last_msg.tool_calls

    results = []
    for tc in tool_calls:
        # 1. 根据 name 找到对应工具
        tool_func = TOOL_MAP.get(tc["name"])

        if tool_func is None:
            # 工具不存在 → 返回错误消息
            results.append(ToolMessage(
                content=f"错误：工具 {tc['name']} 不存在",
                tool_call_id=tc["id"]
            ))
            continue

        try:
            # 2. 执行工具
            output = tool_func(**tc["arguments"])

            # 3. 包装为 ToolMessage
            results.append(ToolMessage(
                content=str(output),
                tool_call_id=tc["id"]
            ))
        except Exception as e:
            results.append(ToolMessage(
                content=f"工具执行错误：{e}",
                tool_call_id=tc["id"]
            ))

    return {"messages": results}
```

---

## 7. 难点五：消息流转全链路追踪

### 7.1 LangGraph 中消息类型的完整体系

```
BaseMessage（基类）
  ├── SystemMessage     ← 系统提示（告诉 LLM 它的角色和规则）
  ├── HumanMessage      ← 用户输入
  ├── AIMessage         ← LLM 回复（可能包含 tool_calls）
  └── ToolMessage       ← 工具执行结果
```

### 7.2 一次完整对话的消息变化追踪

**场景：用户问 "Python 是谁创建的？"，Agent 调用知识库工具后回答。**

```
=== 初始状态 ===
State.messages = []

=== invoke 调用，传入用户消息 ===
State.messages = [
    HumanMessage(content="Python 是谁创建的？")    # ← 用户输入
]

=== 进入 agent 节点 ===
  → agent 节点构造完整消息列表：
    [SystemMessage("你是知识库助手..."), HumanMessage("Python 是谁创建的？")]
  → 发送给 LLM
  → LLM 返回：需要调用 search_knowledge 工具

State.messages = [
    HumanMessage(content="Python 是谁创建的？"),
    AIMessage(content="", tool_calls=[             # ← LLM 决定调用工具
        {"name": "search_knowledge",
         "arguments": {"query": "Python 创建者"},
         "id": "call_abc123"}
    ])
]

=== tools_condition 判断 ===
  → 检测到 tool_calls → 路由到 "tools" 节点

=== 进入 tools 节点 ===
  → 匹配 "search_knowledge" 工具
  → 执行 search_knowledge(query="Python 创建者")
  → 返回 "Python 由 Guido van Rossum 于 1991 年创建。"

State.messages = [
    HumanMessage(content="Python 是谁创建的？"),
    AIMessage(content="", tool_calls=[...]),
    ToolMessage(                                    # ← 工具结果
        content="Python 由 Guido van Rossum 于 1991 年创建。",
        tool_call_id="call_abc123"
    )
]

=== 回到 agent 节点 ===
  → agent 节点将完整消息列表发给 LLM：
    [SystemMessage, HumanMessage, AIMessage(tool_calls), ToolMessage(result)]
  → LLM 基于工具结果生成最终回答

State.messages = [
    HumanMessage(content="Python 是谁创建的？"),
    AIMessage(content="", tool_calls=[...]),
    ToolMessage(content="Python 由 Guido..."),
    AIMessage(content="Python 是由 Guido van Rossum...")  # ← 最终回答
]

=== tools_condition 判断 ===
  → 最后一条消息是 AIMessage，没有 tool_calls → 路由到 END

=== 返回最终 State ===
result["messages"][-1].content = "Python 是由 Guido van Rossum..."
```

### 7.3 多轮对话的消息累积

```
第一轮 invoke:
messages = [Human("你好"), AIMessage("你好！")]

第二轮 invoke（同一 thread_id，Checkpointer 自动恢复历史）:
messages = [
    Human("你好"),              ← 第 1 轮
    AIMessage("你好！"),        ← 第 1 轮
    Human("我叫张三"),          ← 第 2 轮（新增）
]
# LLM 看到完整历史，知道用户叫张三

第三轮 invoke:
messages = [
    Human("你好"),
    AIMessage("你好！"),
    Human("我叫张三"),
    AIMessage("你好张三！"),
    Human("我叫什么？"),        ← 第 3 轮（新增）
]
# LLM 回答 "你叫张三"
```

### 7.4 消息过多时的裁剪策略

```python
def agent_node(state: MessagesState):
    messages = state["messages"]

    # 策略 1：只保留最近 N 条消息
    recent = messages[-10:]

    # 策略 2：保留系统提示 + 最近消息
    full = [SystemMessage(content=SYSTEM_PROMPT)] + recent[-6:]

    # 策略 3：按 Token 数裁剪
    while count_tokens(full) > MAX_TOKENS and len(full) > 2:
        full = [full[0]] + full[2:]  # 保留 SystemMessage，去掉最早的用户消息

    response = call_llm(full)
    return {"messages": [response]}
```

---

## 8. 难点六：Checkpointer 持久化原理

### 8.1 没有 Checkpointer 会怎样

```python
# 不带 Checkpointer
app = builder.compile()

# 第一次调用
r1 = app.invoke({"messages": [HumanMessage("我叫张三")]})
# 对话结束，状态被丢弃

# 第二次调用
r2 = app.invoke({"messages": [HumanMessage("我叫什么？")]})
# Agent 不知道你叫张三！每次都是全新对话
```

### 8.2 MemorySaver：内存持久化

```python
from langgraph.checkpoint.memory import MemorySaver

checkpointer = MemorySaver()
app = builder.compile(checkpointer=checkpointer)

# MemorySaver 在内存中保存每个 thread_id 的状态快照
# 状态结构：
# {
#     "session_001": {
#         "checkpoint_1": {"messages": [Human("我叫张三"), AIMessage("你好张三")]},
#         "checkpoint_2": {"messages": [...]},  # 每次更新都有快照
#     },
#     "session_002": { ... }  # 不同 session 隔离
# }
```

**MemorySaver 的局限：** 程序重启后内存清空，所有对话历史丢失。

### 8.3 数据库持久化（生产推荐）

```python
# SQLite 持久化
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    app = builder.compile(checkpointer=checkpointer)
    # 状态持久化到 SQLite 文件，程序重启后对话历史保留
```

### 8.4 Checkpointer 的工作机制

```
invoke 调用（thread_id = "user_001"）
  │
  ├── 1. Checkpointer 查找 "user_001" 的最新快照
  │      → 如果存在：恢复 State（包含历史消息）
  │      → 如果不存在：State 初始化为空
  │
  ├── 2. 将用户新消息合并到 State
  │
  ├── 3. 执行图（每个节点执行后，自动保存一个快照）
  │      Node A 执行 → 保存快照 checkpoint_1
  │      Node B 执行 → 保存快照 checkpoint_2
  │
  └── 4. 返回结果
```

### 8.5 thread_id 就是会话隔离的钥匙

```python
config_A = {"configurable": {"thread_id": "user_A"}}
config_B = {"configurable": {"thread_id": "user_B"}}

# 用户 A 对话
app.invoke({"messages": [HumanMessage("我叫张三")]}, config_A)

# 用户 B 对话（完全隔离，不知道张三的存在）
app.invoke({"messages": [HumanMessage("我叫李四")]}, config_B)

# 用户 A 继续
r = app.invoke({"messages": [HumanMessage("我叫什么？")]}, config_A)
# 回答 "张三"（因为 thread_id 是 user_A）
```

---

## 9. 难点七：Human-in-the-Loop 完整流程

### 9.1 为什么需要人机协作

某些场景下 Agent 的操作需要人工确认才能执行：

- 删除数据前需要确认
- 发送邮件前需要审核内容
- 支付操作需要人工授权

### 9.2 完整流程拆解

```python
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage

checkpointer = MemorySaver()

# 编译时指定中断点
app = builder.compile(
    checkpointer=checkpointer,
    interrupt_before=["tools"]  # 在 tools 节点执行前暂停
)

config = {"configurable": {"thread_id": "approval_001"}}
```

**第一步：发起请求**

```python
result = app.invoke(
    {"messages": [HumanMessage(content="删除所有知识库数据")]},
    config=config
)

# 执行到 tools 节点前暂停
# result 包含 Agent 决定调用的工具信息
last_msg = result["messages"][-1]
print(last_msg.tool_calls)
# [{"name": "delete_all_data", "arguments": {}, "id": "call_xxx"}]

# 此时图处于暂停状态，等待人工决策
```

**第二步：人工审查**

```python
# 查看当前状态
state = app.get_state(config)
print(state.next)         # ["tools"] — 下一步要执行的节点
print(state.values)       # 当前完整的 State

# 人工决策：批准 或 拒绝
user_decision = input("Agent 要执行 delete_all_data，批准吗？(y/n): ")
```

**第三步 A：批准执行**

```python
if user_decision == "y":
    # 传 None 继续（从中断点恢复）
    result = app.invoke(None, config=config)
    # tools 节点执行，数据被删除
```

**第三步 B：拒绝执行**

```python
else:
    # 修改 State，添加一条拒绝消息，跳过工具执行
    from langchain_core.messages import ToolMessage

    # 用 ToolMessage 回复（匹配 tool_call_id），告知 LLM 操作被拒绝
    app.update_state(
        config,
        {"messages": [
            ToolMessage(
                content="操作被用户拒绝",
                tool_call_id=last_msg.tool_calls[0]["id"]
            )
        ]}
    )

    # 继续执行（Agent 收到拒绝消息后会告知用户）
    result = app.invoke(None, config=config)
```

### 9.3 interrupt_before vs interrupt_after

```python
# interrupt_before：进入节点前暂停
app = builder.compile(interrupt_before=["tools"])
# 流程：... → agent → [暂停] → tools → ...
# 用途：审批工具调用

# interrupt_after：节点执行完后暂停
app = builder.compile(interrupt_after=["agent"])
# 流程：... → agent → [暂停] → tools → ...
# 用途：审查 Agent 的决策
```

---

## 10. 难点八：编译与运行时行为

### 10.1 compile() 做了什么

```python
app = builder.compile(checkpointer=checkpointer)
```

compile() 内部完成：

```
1. 验证图的完整性
   ├── 检查所有节点是否已注册（add_node）
   ├── 检查边引用的节点是否存在
   ├── 检查是否存在从 START 可达的路径
   └── 检查是否有节点无法到达 END

2. 构建执行计划
   ├── 确定节点的执行顺序
   └── 解析条件边的所有可能路径

3. 注入 Checkpointer
   └── 在每个节点执行前后插入状态保存逻辑

4. 返回 CompiledGraph 对象
   ├── .invoke()   → 同步执行
   ├── .stream()   → 流式执行
   ├── .ainvoke()  → 异步执行
   ├── .astream()  → 异步流式
   ├── .get_state()      → 获取当前状态
   └── .get_state_history() → 获取历史状态
```

### 10.2 invoke vs stream 的区别

```python
# invoke：等整个图执行完，一次性返回结果
result = app.invoke(input, config)
# 只有最终 State

# stream：每执行完一个节点，立即返回该节点的输出
for chunk in app.stream(input, config):
    print(chunk)
    # {"agent": {"messages": [AIMessage(tool_calls=[...])]}}
    # {"tools": {"messages": [ToolMessage(...)]}}
    # {"agent": {"messages": [AIMessage(content="最终回答")]}}
```

**stream 的每个 chunk 结构：**

```python
# chunk 的 key 是节点名，value 是该节点返回的更新
chunk = {
    "agent": {           # 节点名
        "messages": [AIMessage(content="最终回答")]
    }
}

# 可以根据节点名过滤
for chunk in app.stream(input, config):
    if "agent" in chunk:
        msg = chunk["agent"]["messages"][-1]
        if msg.content:
            print(msg.content)  # 只打印 Agent 的文本输出
```

---

## 11. 难点九：图的无限循环防护

### 11.1 为什么会无限循环

```
START → agent → tools → agent → tools → agent → tools → ...
```

如果 LLM 持续返回 `tool_calls`，Agent 和 Tools 就会无限循环。

### 11.2 防护方案一：递归限制

```python
# compile 时设置最大递归深度
app = builder.compile(
    checkpointer=checkpointer,
    recursion_limit=10  # 最多执行 10 个 super-step
)

# 超过限制会抛出 GraphRecursionError
try:
    result = app.invoke(input, config)
except GraphRecursionError:
    print("Agent 执行步数超限，可能陷入循环")
```

### 11.3 防护方案二：在 Prompt 中限制

```python
SYSTEM_PROMPT = """你是一个智能助手。

重要规则：
1. 最多连续调用 3 次工具
2. 如果连续调用工具后仍无法回答，请直接告知用户
3. 不要重复调用同一个工具
"""
```

### 11.4 防护方案三：节点内部计数

```python
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    tool_call_count: int  # 工具调用计数

def agent_node(state: AgentState) -> dict:
    count = state.get("tool_call_count", 0)

    if count >= 3:
        # 强制 LLM 不使用工具，直接回答
        response = call_llm(state["messages"], tools=None)
        return {"messages": [response]}

    response = call_llm(state["messages"], tools=ALL_TOOLS)

    update = {"messages": [response]}
    if response.tool_calls:
        update["tool_call_count"] = count + 1
    else:
        update["tool_call_count"] = 0  # 重置计数

    return update
```

---

## 12. 难点十：多 Agent 协作模式

### 12.1 模式一：Supervisor（主管模式）

一个中心 Agent 负责分发任务给专业 Agent：

```python
from langgraph.graph import StateGraph, MessagesState, START, END

# 专业 Agent
def research_agent(state):
    """负责搜索和研究"""
    ...

def code_agent(state):
    """负责写代码"""
    ...

def writer_agent(state):
    """负责写文案"""
    ...

# 主管 Agent
def supervisor(state):
    """分析任务，决定分配给哪个 Agent"""
    task = state["messages"][-1].content
    response = call_llm(f"这个任务应该给谁：{task}\n选项：research/code/writer")
    return response

def route_to_agent(state):
    last = state["messages"][-1].content.lower()
    if "research" in last: return "research"
    if "code" in last: return "code"
    if "writer" in last: return "writer"
    return END

# 构建图
builder = StateGraph(MessagesState)
builder.add_node("supervisor", supervisor)
builder.add_node("research", research_agent)
builder.add_node("code", code_agent)
builder.add_node("writer", writer_agent)

builder.add_edge(START, "supervisor")
builder.add_conditional_edges("supervisor", route_to_agent)
builder.add_edge("research", END)
builder.add_edge("code", END)
builder.add_edge("writer", END)
```

```
         START
           │
           ▼
      ┌──────────┐
      │ Supervisor │ ← 分析任务
      └─────┬─────┘
            │ 条件路由
    ┌───────┼───────┐
    ▼       ▼       ▼
Research  Code   Writer   ← 专业 Agent 执行
    │       │       │
    └───────┼───────┘
            ▼
           END
```

### 12.2 模式二：Swarm（群智模式）

多个 Agent 平等协作，每个 Agent 可以把任务交给另一个 Agent：

```python
def research_agent(state):
    response = call_llm(state["messages"], tools=research_tools)
    return {"messages": [response]}

def code_agent(state):
    response = call_llm(state["messages"], tools=code_tools)
    return {"messages": [response]}

def route_after_research(state):
    last = state["messages"][-1]
    if hasattr(last, "tool_calls"):
        for tc in last.tool_calls:
            if tc["name"] == "hand_off_to_code":
                return "code_agent"
        return "research_tools"
    return END

builder.add_node("research_agent", research_agent)
builder.add_node("code_agent", code_agent)
builder.add_conditional_edges("research_agent", route_after_research)
```

---

## 13. 难点十一：错误处理与重试策略

### 13.1 节点级别的错误处理

```python
def safe_agent_node(state: MessagesState) -> dict:
    """带错误处理的 Agent 节点"""
    try:
        messages = state["messages"]
        response = call_llm(messages)

        # 检查 LLM 返回是否有效
        if not response:
            return {"messages": [AIMessage(content="抱歉，我暂时无法回答。")]}

        return {"messages": [response]}

    except Exception as e:
        # 不抛异常，而是返回错误消息让图继续运行
        error_msg = f"Agent 处理出错：{type(e).__name__}"
        return {"messages": [AIMessage(content=error_msg)]}
```

### 13.2 工具级别的错误处理

```python
@tool
def search_knowledge(query: str) -> str:
    """搜索知识库（带错误处理）"""
    try:
        results = vector_db.search(query)
        if not results:
            return "未找到相关内容。"
        return format_results(results)
    except ConnectionError:
        return "知识库连接失败，请稍后重试。"
    except Exception as e:
        return f"搜索出错：{e}"
```

### 13.3 带重试的 LLM 调用

```python
import time

def call_llm_with_retry(messages, tools=None, max_retries=3):
    """带重试和退避的 LLM 调用"""
    for attempt in range(max_retries):
        try:
            return completion(
                model="deepseek/deepseek-chat",
                messages=messages,
                tools=tools,
                api_key="your-key"
            )
        except RateLimitError:
            wait = 2 ** attempt  # 1s, 2s, 4s
            print(f"触发限流，等待 {wait}s 后重试...")
            time.sleep(wait)
        except APIConnectionError:
            if attempt < max_retries - 1:
                time.sleep(1)
            else:
                raise
    raise Exception(f"LLM 调用失败，已重试 {max_retries} 次")
```

---

## 14. 难点十二：调试与问题排查

### 14.1 打印每步的 State

```python
def debug_node(name):
    """创建一个调试节点，打印当前 State"""
    def _debug(state: MessagesState):
        print(f"\n=== [{name}] 节点执行 ===")
        print(f"消息数量: {len(state['messages'])}")
        for i, msg in enumerate(state['messages']):
            msg_type = type(msg).__name__
            content = str(msg.content)[:80] if msg.content else "(无内容)"
            tool_calls = getattr(msg, 'tool_calls', None)
            print(f"  [{i}] {msg_type}: {content}")
            if tool_calls:
                for tc in tool_calls:
                    print(f"       → tool_call: {tc['name']}({tc['arguments']})")
        return {}  # 不修改 State
    return _debug

# 在图的任意位置插入调试节点
builder.add_node("debug_1", debug_node("Agent 之后"))
builder.add_edge("agent", "debug_1")
builder.add_edge("debug_1", "tools")
```

### 14.2 使用 stream 逐步查看输出

```python
# stream 模式可以看到每个节点的输出
for chunk in app.stream(
    {"messages": [HumanMessage(content="Python 是谁创建的？")]},
    config={"configurable": {"thread_id": "debug"}}
):
    node_name = list(chunk.keys())[0]
    print(f"\n--- 节点 {node_name} 输出 ---")
    messages = chunk[node_name].get("messages", [])
    for msg in messages:
        print(f"  {type(msg).__name__}: {str(msg.content)[:100]}")
        if hasattr(msg, 'tool_calls') and msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"  → 调用工具: {tc['name']}({tc['arguments']})")

# 输出示例：
# --- 节点 agent 输出 ---
#   AIMessage:
#   → 调用工具: search_knowledge({'query': 'Python 创建者'})
#
# --- 节点 tools 输出 ---
#   ToolMessage: Python 由 Guido van Rossum 于 1991 年创建。
#
# --- 节点 agent 输出 ---
#   AIMessage: Python 是由 Guido van Rossum 在 1991 年创建的编程语言。
```

### 14.3 使用 get_state 检查当前状态

```python
# 查看当前状态
state = app.get_state(config)
print(f"下一步要执行: {state.next}")      # ['agent'] 或 ['tools']
print(f"消息数: {len(state.values['messages'])}")
print(f"配置: {state.config}")

# 查看完整历史（Time Travel）
for state in app.get_state_history(config):
    print(f"Step {state.metadata['step']}: next={state.next}")
```

### 14.4 可视化图结构

```python
# 生成图的 Mermaid 图表
from IPython.display import Image, display

# 需要 pip install grandalf
display(Image(app.get_graph().draw_mermaid_png()))

# 或者打印 ASCII 图
print(app.get_graph().print_ascii())
```

---

## 15. 完整实战：从零构建 RAG Agent

### 15.1 完整代码

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
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langchain_core.messages import (
    HumanMessage, SystemMessage, AIMessage, ToolMessage
)
from pydantic import BaseModel, Field

# ============================================
# 1. 配置
# ============================================
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
def agent_node(state: MessagesState) -> dict:
    """Agent 推理节点"""
    from litellm import completion

    # 构造消息：系统提示 + 历史 + 当前
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]

    # 裁剪过长历史（保留最近 20 条）
    if len(messages) > 22:  # 1 system + 20 history + 1 current
        messages = [messages[0]] + messages[-21:]

    # 调用 LLM
    response = completion(
        model=os.getenv("LLM_PROVIDER", "deepseek") + "/" + os.getenv("LLM_MODEL", "deepseek-chat"),
        messages=[{"role": m.type if hasattr(m, "type") else "user",
                   "content": m.content if m.content else ""}
                  for m in messages],
        tools=[t.get_function_schema() for t in ALL_TOOLS],
        temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
        api_key=os.getenv("LLM_API_KEY"),
        api_base=os.getenv("LLM_API_BASE"),
    )

    ai_message = response.choices[0].message

    # 将 LiteLLM 响应转为 LangChain AIMessage
    msg = AIMessage(
        content=ai_message.content or "",
        tool_calls=getattr(ai_message, "tool_calls", None)
    )

    return {"messages": [msg]}

# ============================================
# 4. 构建图
# ============================================
builder = StateGraph(MessagesState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(ALL_TOOLS))

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

# ============================================
# 5. 编译（带持久化 + 递归限制）
# ============================================
checkpointer = MemorySaver()
app = builder.compile(
    checkpointer=checkpointer,
    recursion_limit=10  # 防止无限循环
)

# ============================================
# 6. 运行
# ============================================
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

### 15.2 关键设计决策总结

| 决策 | 选择 | 原因 |
|------|------|------|
| State 类型 | `MessagesState` | 标准 Agent 模式，自动消息追加 |
| 工具节点 | 预置 `ToolNode` | 自动处理 tool_calls → ToolMessage 转换 |
| 条件路由 | `tools_condition` | 标准 Agent 模式的默认路由 |
| 持久化 | `MemorySaver` | 开发阶段用内存，生产换 SQLite |
| 递归限制 | 10 | 防止 Agent-Tools 无限循环 |
| 消息裁剪 | 最近 20 条 | 控制 Token 消耗 |
