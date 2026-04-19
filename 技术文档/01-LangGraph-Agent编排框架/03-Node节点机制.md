# LangGraph — Node 节点内部运作

---

## 节点到底是什么

节点就是一个 **Python 函数**，签名为：

每个节点只做三件事：从 State 中读取数据、执行自己的业务逻辑、返回需要更新的字段。LangGraph 框架负责在节点之间传递 State、调用 Reducer 合并更新。这种设计让每个节点保持独立和简单——你不需要关心其他节点的存在，只需要关注"给我什么数据、我返回什么数据"。

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

这种"只返回差异"的设计是为了避免节点之间的耦合。如果一个节点必须返回完整 State，那么每次增加一个新字段，所有节点都要改。只返回需要更新的字段，新字段对不相关节点完全透明。

---

## 节点的完整生命周期

每个节点被 LangGraph 调用时，都经历三个阶段。第一阶段是"读取"：框架把当前 State 传给你的函数。第二阶段是"执行"：你在函数里做任何事——调用 LLM、查询数据库、执行计算。第三阶段是"返回更新"：你返回一个字典，框架通过 Reducer 把它合并到 State 中。

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

---

## 节点可以返回空更新

返回空字典 `{}` 是合法的，表示"我不修改任何字段"。这在某些场景下很有用：日志记录节点只打印信息不改 State，或者某些条件判断节点只需要读取 State 做路由决策但不需要写入。空更新不会触发 Reducer，State 完全不变。

```python
def log_node(state: MessagesState) -> dict:
    """只做日志记录，不修改 State"""
    print(f"当前消息数: {len(state['messages'])}")
    return {}  # 空字典 = 不更新任何字段
```

---

## 同步节点 vs 异步节点

LangGraph 同时支持同步和异步节点，你可以根据节点的 I/O 特性来选择。如果你的节点主要做 CPU 计算，用同步函数就足够了。如果节点涉及大量等待（比如调用外部 API、访问数据库、请求 LLM），用异步函数可以让多个 I/O 操作并发执行，大幅提升性能。

实际选择建议：开发阶段用同步函数更简单直观，上线后遇到性能瓶颈时再把 I/O 密集型节点改为异步。LangGraph 自动识别函数类型，你不需要额外配置。

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
