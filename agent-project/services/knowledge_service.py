import uuid
import json
from config.settings import settings
from db.sqlite_manager import sqlite_manager
from db.vector_manager import vector_manager


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> list[str]:
    """智能文本分块：在句号、问号、感叹号等处切分"""
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        if end < len(text):
            for sep in ["。", "！", "？", ".", "!", "?", "\n"]:
                pos = text.rfind(sep, start + chunk_size - overlap, end)
                if pos != -1:
                    end = pos + 1
                    break
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def import_knowledge(title: str, content: str, source: str = "manual") -> tuple[str, int]:
    """导入知识文档"""
    chunks = chunk_text(content)
    doc_id = f"doc_{uuid.uuid4().hex[:8]}"

    sqlite_manager.save_document_meta(doc_id, title, source, len(chunks))

    records = [
        {
            "doc_id": doc_id,
            "chunk_id": f"{doc_id}_{i}",
            "title": title,
            "content": chunk,
            "metadata": json.dumps({"chunk_index": i, "source": source}),
        }
        for i, chunk in enumerate(chunks)
    ]
    vector_manager.insert_records("knowledge_chunks", records)

    return doc_id, len(chunks)


def search_knowledge(query: str, top_k: int = None) -> list[dict]:
    """搜索知识库"""
    return vector_manager.search(
        table_name="knowledge_chunks",
        query_text=query,
        limit=top_k or settings.VECTOR_SEARCH_LIMIT,
    )


def get_knowledge_stats() -> dict:
    return sqlite_manager.get_knowledge_stats()


def list_documents() -> list[dict]:
    return sqlite_manager.list_documents()


def delete_knowledge(doc_id: str):
    sqlite_manager.delete_document(doc_id)
    vector_manager.delete_by_doc_id("knowledge_chunks", doc_id)
