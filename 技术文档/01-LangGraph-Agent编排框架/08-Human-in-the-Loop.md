# LangGraph — Human-in-the-Loop 完整流程

---

## 为什么需要人机协作

某些场景下 Agent 的操作需要人工确认才能执行：

- 删除数据前需要确认
- 发送邮件前需要审核内容
- 支付操作需要人工授权

Human-in-the-Loop（人机协作）是 LangGraph 的重要特性。它的工作原理是利用 Checkpointer 的状态保存能力，在图的执行过程中暂停，等待人工做出决策后再继续。本质上就是"执行到某个节点前/后暂停 → 人工查看并决策 → 恢复执行"。这需要 Checkpointer，因为暂停意味着要保存当前 State，恢复时要能还原。

---

## 完整流程拆解

人机协作的完整流程分为三步。第一步：正常发起请求，图会执行到指定的中断点后暂停。第二步：人工通过 `get_state` 查看当前状态，判断 Agent 准备做什么。第三步：人工做出决策——批准则传 `None` 继续执行，拒绝则通过 `update_state` 注入一条拒绝消息让 Agent 知道操作被拒绝。

```python
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage

checkpointer = InMemorySaver()

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

---

## interrupt_before vs interrupt_after

两种中断方式的区别在于暂停的时机。`interrupt_before` 在目标节点执行前暂停，适合"审批工具调用"场景——你想在工具真正执行前拦截。`interrupt_after` 在目标节点执行完后暂停，适合"审查 Agent 决策"场景——你想看看 Agent 做了什么决定再决定是否放行。

实际使用中，`interrupt_before=["tools"]` 是最常见的配置，因为大多数审批需求都是"在危险操作执行前拦截"。

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
