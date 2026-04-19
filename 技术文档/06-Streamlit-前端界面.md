# Streamlit — 前端界面技术文档

---

## 1. 技术概述

Streamlit 是一个 Python 前端框架，用纯 Python 代码快速构建数据应用和 AI 聊天界面，无需 HTML/CSS/JavaScript。

| 项目 | 说明 |
|------|------|
| 版本 | 1.38.0 |
| 语言 | Python |
| 官方文档 | https://docs.streamlit.io/ |
| 安装 | `pip install streamlit==1.38.0` |
| 核心价值 | 纯 Python 构建交互式 Web 界面 |

---

## 2. 安装与运行

### 2.1 安装

```bash
pip install streamlit==1.38.0
```

### 2.2 创建并运行应用

```python
# ui/app.py
import streamlit as st

st.title("Agent 智能助手")
st.write("欢迎使用知识库问答系统")
```

```bash
streamlit run ui/app.py
# 自动打开浏览器 http://localhost:8501
```

---

## 3. 核心组件

### 3.1 聊天界面组件

```python
import streamlit as st

# 聊天消息展示
st.chat_message("user").write("你好")
st.chat_message("assistant").write("你好！有什么可以帮你的？")

# 聊天输入框
prompt = st.chat_input("输入你的问题...")
if prompt:
    st.chat_message("user").write(prompt)
    with st.chat_message("assistant"):
        response = call_agent(prompt)
        st.write(response)
```

### 3.2 输入组件

```python
import streamlit as st

# 文本输入
name = st.text_input("名称", placeholder="请输入")

# 文本区域
content = st.text_area("内容", height=200)

# 数字输入
top_k = st.number_input("返回数量", min_value=1, max_value=20, value=5)

# 按钮
if st.button("提交"):
    st.success("提交成功")

# 选择框
model = st.selectbox("选择模型", ["deepseek-chat", "gpt-4", "claude-3"])

# 滑块
temperature = st.slider("Temperature", 0.0, 1.0, 0.7)
```

### 3.3 布局组件

```python
import streamlit as st

# 侧边栏
with st.sidebar:
    st.title("设置")
    model = st.selectbox("模型", ["deepseek-chat", "gpt-4"])
    temperature = st.slider("Temperature", 0.0, 1.0, 0.7)

# 分栏
col1, col2 = st.columns(2)
with col1:
    st.write("左栏")
with col2:
    st.write("右栏")

# 标签页
tab1, tab2 = st.tabs(["对话", "知识库"])
with tab1:
    st.write("对话界面")
with tab2:
    st.write("知识库管理")

# 折叠面板
with st.expander("高级设置"):
    st.write("隐藏的高级选项")
```

### 3.4 状态管理

```python
import streamlit as st

# session_state 在用户会话期间保持数据
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "default"

# 读取和修改
st.session_state.messages.append({"role": "user", "content": "你好"})
print(st.session_state.thread_id)
```

---

## 4. 完整聊天界面实现

```python
# ui/app.py
import streamlit as st
import requests

# === 页面配置 ===
st.set_page_config(
    page_title="Agent 智能助手",
    page_icon="🤖",
    layout="wide"
)

# === 初始化状态 ===
if "messages" not in st.session_state:
    st.session_state.messages = []

if "thread_id" not in st.session_state:
    st.session_state.thread_id = "session_001"

# === 侧边栏 ===
with st.sidebar:
    st.title("⚙️ 设置")

    thread_id = st.text_input("会话 ID", value=st.session_state.thread_id)
    st.session_state.thread_id = thread_id

    if st.button("🗑️ 清空对话"):
        st.session_state.messages = []
        st.rerun()

    st.divider()
    st.subheader("📚 知识库管理")

    with st.expander("导入文本知识"):
        doc_title = st.text_input("文档标题", key="import_title")
        doc_content = st.text_area("文档内容", height=150, key="import_content")
        if st.button("导入"):
            if doc_title and doc_content:
                resp = requests.post("http://localhost:8000/api/knowledge/import/text", json={
                    "title": doc_title,
                    "content": doc_content
                })
                if resp.status_code == 200:
                    st.success(f"导入成功，共 {resp.json()['result']['chunk_count']} 个分块")

    with st.expander("搜索知识库"):
        search_query = st.text_input("搜索", key="search_q")
        if st.button("搜索"):
            resp = requests.post("http://localhost:8000/api/knowledge/search", json={
                "query": search_query,
                "top_k": 3
            })
            if resp.status_code == 200:
                for item in resp.json()["result"]:
                    st.markdown(f"**{item['title']}**")
                    st.caption(item["content"][:200])
                    st.divider()

# === 主聊天界面 ===
st.title("🤖 Agent 智能助手")
st.caption("基于 LangGraph + RAG 的知识库问答系统")

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# 聊天输入
if prompt := st.chat_input("输入你的问题..."):
    # 显示用户消息
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # 调用 Agent API
    with st.chat_message("assistant"):
        with st.spinner("思考中..."):
            try:
                resp = requests.post("http://localhost:8000/api/chat", json={
                    "message": prompt,
                    "thread_id": st.session_state.thread_id
                })
                if resp.status_code == 200:
                    answer = resp.json()["result"]
                    st.write(answer)
                    st.session_state.messages.append(
                        {"role": "assistant", "content": answer}
                    )
                else:
                    st.error(f"请求失败: {resp.status_code}")
            except Exception as e:
                st.error(f"连接失败: {e}")
```

### 4.1 运行效果

```
┌──────────────────────────────────────────────────────┐
│  🤖 Agent 智能助手                                    │
│  基于 LangGraph + RAG 的知识库问答系统                   │
│                                                      │
│  👤 你好，请问什么是深度学习？                           │
│                                                      │
│  🤖 深度学习是机器学习的一个子集，使用多层神经网络...      │
│                                                      │
│  👅 深度学习和机器学习有什么区别？                        │
│                                                      │
│  🤖 主要区别在于模型结构...                             │
│                                                      │
│  ┌──────────────────────────────┐                    │
│  │ 输入你的问题...              │                    │
│  └──────────────────────────────┘                    │
├───────────┐                                          │
│ ⚙️ 设置    │                                          │
│ 会话 ID   │                                          │
│ [session] │                                          │
│ [清空对话] │                                          │
│ ─────────│                                          │
│ 📚 知识库  │                                          │
│ ▶ 导入文本 │                                          │
│ ▶ 搜索    │                                          │
└───────────┘                                          │
└──────────────────────────────────────────────────────┘
```

---

## 5. 流式输出实现

```python
# ui/app.py（流式版本核心代码）
import json
import requests

if prompt := st.chat_input("输入你的问题..."):
    st.chat_message("user").write(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("assistant"):
        response_text = st.empty()
        full_text = ""

        # 使用 SSE 流式接口
        resp = requests.post(
            "http://localhost:8000/api/chat/stream",
            json={"message": prompt, "thread_id": st.session_state.thread_id},
            stream=True
        )

        for line in resp.iter_lines():
            if line:
                line = line.decode()
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    chunk_data = json.loads(data)
                    full_text += chunk_data.get("content", "")
                    response_text.write(full_text)

        st.session_state.messages.append(
            {"role": "assistant", "content": full_text}
        )
```

---

## 6. 常见问题

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 页面频繁刷新 | 在回调中修改全局状态 | 使用 `st.session_state` |
| 组件状态丢失 | 未绑定 key | 给每个组件设置唯一 `key` |
| API 连接失败 | 后端未启动 | 先启动 FastAPI 服务 |
| 中文显示乱码 | 编码问题 | 文件保存为 UTF-8 |
| 样式不好看 | 默认样式简陋 | 使用 `st.markdown` 自定义 CSS |
