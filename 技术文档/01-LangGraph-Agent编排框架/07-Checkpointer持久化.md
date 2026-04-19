# LangGraph — Checkpointer 持久化原理

---

## 没有 Checkpointer 会怎样

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

---

## InMemorySaver：内存持久化

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
app = builder.compile(checkpointer=checkpointer)

# InMemorySaver 在内存中保存每个 thread_id 的状态快照
# 状态结构：
# {
#     "session_001": {
#         "checkpoint_1": {"messages": [Human("我叫张三"), AIMessage("你好张三")]},
#         "checkpoint_2": {"messages": [...]},  # 每次更新都有快照
#     },
#     "session_002": { ... }  # 不同 session 隔离
# }
```

> **注意：** 旧版本中该类名为 `MemorySaver`，从 `langgraph-checkpoint 2.1.0` 起已改名为 `InMemorySaver`。
> 旧导入 `from langgraph.checkpoint.memory import MemorySaver` 将在后续版本中移除。

**InMemorySaver 的局限：** 程序重启后内存清空，所有对话历史丢失。

---

## 数据库持久化（生产推荐）

```python
# SQLite 持久化（需额外安装：pip install langgraph-checkpoint-sqlite）
from langgraph.checkpoint.sqlite import SqliteSaver

with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    app = builder.compile(checkpointer=checkpointer)
    # 状态持久化到 SQLite 文件，程序重启后对话历史保留

# PostgreSQL 持久化（需额外安装：pip install langgraph-checkpoint-postgres）
from langgraph.checkpoint.postgres import PostgresSaver

DB_URI = "postgresql://user:pass@localhost:5432/dbname"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    app = builder.compile(checkpointer=checkpointer)
    # 适合生产环境，支持并发访问
```

---

## Checkpointer 的工作机制

```mermaid
flowchart TD
    A["invoke 调用（thread_id = 'user_001'）"] --> B["1. Checkpointer 查找最新快照"]
    B --> C{"快照是否存在？"}
    C -->|存在| D["恢复 State（包含历史消息）"]
    C -->|不存在| E["State 初始化为空"]
    D --> F["2. 将用户新消息合并到 State"]
    E --> F
    F --> G["3. 执行图（每个节点执行后自动保存快照）"]
    G --> H["Node A 执行 → 保存 checkpoint_1"]
    H --> I["Node B 执行 → 保存 checkpoint_2"]
    I --> J["4. 返回结果"]
```

---

## thread_id 就是会话隔离的钥匙

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
