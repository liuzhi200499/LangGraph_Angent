"""
Streamlit 前端界面
提供 Agent 智能助手的可视化交互界面，包括：
- 多轮对话（支持上下文记忆）
- 知识库导入和统计查看
- 新建对话功能

启动命令：streamlit run ui/app.py
"""
import streamlit as st


def init_session_state():
    """初始化 Streamlit 会话状态，用于在页面重载时保持对话上下文"""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None     # 当前会话线程ID
    if "messages" not in st.session_state:
        st.session_state.messages = []         # 当前对话的消息列表


def main():
    # 页面基本配置
    st.set_page_config(page_title="Agent 智能助手", page_icon="🤖", layout="wide")
    st.title("🤖 Agent 智能知识库助手")

    init_session_state()

    # ==================== 侧边栏 ====================
    with st.sidebar:
        st.header("设置")
        # 新建对话按钮：清空当前会话状态，重新开始
        if st.button("新建对话"):
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.header("知识库管理")

        # 知识导入面板（可折叠）
        with st.expander("导入知识"):
            title = st.text_input("文档标题", key="import_title")
            content = st.text_area("文档内容", height=200, key="import_content")
            if st.button("导入"):
                if title and content:
                    from services.knowledge_service import import_knowledge
                    doc_id, chunk_count = import_knowledge(title, content)
                    st.success(f"导入成功！文档ID: {doc_id}，分块数: {chunk_count}")
                else:
                    st.warning("请填写标题和内容")

        # 知识库统计面板（可折叠）
        with st.expander("知识库统计"):
            if st.button("查看统计"):
                from services.knowledge_service import get_knowledge_stats
                stats = get_knowledge_stats()
                st.write(f"文档数量: {stats['document_count']}")
                st.write(f"知识分块: {stats['total_chunks']}")

    # ==================== 对话区域 ====================

    # 渲染历史消息
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 聊天输入框，用户输入后触发对话
    if prompt := st.chat_input("输入你的问题..."):
        # 显示用户消息
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # 调用 Agent 获取回复
        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                from services.chat_service import ChatService
                service = ChatService()
                response, thread_id = service.chat(
                    message=prompt,
                    thread_id=st.session_state.thread_id,
                )
                st.session_state.thread_id = thread_id  # 保存 thread_id 保持会话连续
                st.markdown(response)

        # 保存 AI 回复到会话状态
        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
