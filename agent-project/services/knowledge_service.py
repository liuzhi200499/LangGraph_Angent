"""
知识库服务模块
提供知识文档的导入、搜索、删除等功能。
处理流程：文档 → 智能文本分块 → 向量化 → MenteeDB 存储。
"""
import uuid
import json
from config.settings import settings
from db.sqlite_manager import sqlite_manager
from db.vector_manager import vector_manager


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """
    智能文本分块
    在句号、问号、感叹号等标点处切分，保证每个文本块的语义完整性。
    相邻块之间保留 overlap 重叠部分，避免关键信息被截断在块边界。

    参数:
        text: 待分块的原始文本
        chunk_size: 每块最大字符数，默认取配置值 500
        overlap: 相邻块重叠字符数，默认取配置值 50
    返回:
        文本块列表
    """
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            # 在分块末尾附近查找最佳切分点（标点符号），优先在完整句子处断开
            for sep in ["。", "！", "？", ".", "!", "?", "\n"]:
                pos = text.rfind(sep, start + chunk_size - overlap, end)
                if pos != -1:
                    end = pos + 1  # 包含标点符号本身
                    break
        chunks.append(text[start:end])
        start = end - overlap  # 起始位置回退 overlap，保证上下文连续
    return chunks


def import_knowledge(title: str, content: str, source: str = "manual") -> tuple[str, int]:
    """
    导入知识文档
    完整流程：文本分块 → 写入 SQLite 元数据 → 批量写入 MenteeDB 向量库

    参数:
        title: 文档标题
        content: 文档正文内容
        source: 来源标记（manual / wiki / file 等）
    返回:
        (文档ID, 分块数量)
    """
    # 第一步：将长文本切分为多个语义完整的文本块
    chunks = chunk_text(content)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"  # 生成唯一文档ID

    # 第二步：在 SQLite 中保存文档元数据
    sqlite_manager.save_document_meta(doc_id, title, source, len(chunks))

    # 第三步：构建向量记录并批量写入 MenteeDB
    records = [
        {
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}_{i}",       # 每个分块的唯一标识
            "title": title,
            "content": chunk,                   # content 字段会被自动向量化索引
            "metadata": json.dumps({"chunk_index": i, "source": source}),
        }
        for i, chunk in enumerate(chunks)
    ]
    vector_manager.insert_records("knowledge_chunks", records)

    return doc_id, len(chunks)


def search_knowledge(query: str, top_k: int = None) -> list[dict]:
    """
    在知识库中进行语义搜索
    将查询文本向量化后，在 MenteeDB 中查找最相似的知识片段。
    """
    return vector_manager.search(
        table_name="knowledge_chunks",
        query_text=query,
        limit=top_k or settings.VECTOR_SEARCH_LIMIT,
    )


def get_knowledge_stats() -> dict:
    """获取知识库统计数据（文档数、分块数）"""
    return sqlite_manager.get_knowledge_stats()


def list_documents() -> list[dict]:
    """获取所有活跃状态的文档列表"""
    return sqlite_manager.list_documents()


def delete_knowledge(doc_id: str):
    """删除知识文档（SQLite 软删除 + MenteeDB 向量记录删除）"""
    sqlite_manager.delete_document(doc_id)
    vector_manager.delete_by_doc_id("knowledge_chunks", doc_id)
