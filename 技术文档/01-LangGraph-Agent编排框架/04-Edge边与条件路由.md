# LangGraph — Edge 边与条件路由

---

## 固定边：无条件跳转

固定边是最简单的连接方式：A 执行完必定执行 B，没有任何条件判断。它适合逻辑固定的流程，比如"工具节点执行完必须回到 Agent 节点"这种不变的规则。

```python
builder.add_edge(START, "agent")   # 入口 → 永远先执行 agent
builder.add_edge("tools", "agent")  # tools 执行完 → 永远回到 agent
builder.add_edge("respond", END)    # respond 执行完 → 结束
```

**固定边 = 写死的箭头，不看任何条件。**

---

## 条件边：根据 State 动态路由

固定边无法处理"根据情况走不同路径"的需求。条件边让你根据当前 State 的内容动态决定下一个节点。路由函数接收 State 作为参数，返回目标节点的名称字符串。LangGraph 根据返回值找到对应节点并执行。这是 Agent 模式中最核心的机制——Agent 的行为本身就是动态的，它每次都可能做出不同的决策。

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

---

## 内置路由函数：tools_condition

LangGraph 预置了 `tools_condition`，这是最常用的路由函数。理解它的内部逻辑非常重要，因为绝大多数 Agent 都依赖它来决定"是继续调用工具还是结束对话"。

它的判断逻辑很简单：看最后一条消息（LLM 的回复）里有没有 `tool_calls`。如果有，说明 LLM 想调用工具，路由到工具节点；如果没有，说明 LLM 已经给出最终答案，结束对话。

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

---

## 自定义多路分支路由

当你的 Agent 需要两个以上的出口时（比如调用工具、转人工、进入审核、直接结束），就需要写自定义路由函数。路由函数的返回值是目标节点名，你还可以传入一个映射字典来建立返回值到实际节点的对应关系。

注意：路由函数返回的每个节点名都必须已经通过 `add_node` 注册过，否则运行时会抛出 `KeyError`。

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

---

## 边连接的常见错误

新手在使用边时最容易犯两类错误。第一类是遗漏回路边：Agent 调用工具后，工具的结果需要回到 Agent 继续推理，如果错误地把工具节点连到 END，Agent 就看不到工具结果了。第二类是路由函数返回了未注册的节点名，这会在运行时直接报错。

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
