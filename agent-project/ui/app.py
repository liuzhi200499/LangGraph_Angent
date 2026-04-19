import streamlit as st


def init_session_state():
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None
    if "messages" not in st.session_state:
        st.session_state.messages = []


def main():
    st.set_page_config(page_title="Agent 智能助手", page_icon="🤖", layout="wide")
    st.title("🤖 Agent 智能知识库助手")

    init_session_state()

    with st.sidebar:
        st.header("设置")
        if st.button("新建对话"):
            st.session_state.thread_id = None
            st.session_state.messages = []
            st.rerun()

        st.divider()
        st.header("知识库管理")
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

        with st.expander("知识库统计"):
            if st.button("查看统计"):
                from services.knowledge_service import get_knowledge_stats
                stats = get_knowledge_stats()
                st.write(f"文档数量: {stats['document_count']}")
                st.write(f"知识分块: {stats['total_chunks']}")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("输入你的问题..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            with st.spinner("思考中..."):
                from services.chat_service import ChatService
                service = ChatService()
                response, thread_id = service.chat(
                    message=prompt,
                    thread_id=st.session_state.thread_id,
                )
                st.session_state.thread_id = thread_id
                st.markdown(response)

        st.session_state.messages.append({"role": "assistant", "content": response})


if __name__ == "__main__":
    main()
