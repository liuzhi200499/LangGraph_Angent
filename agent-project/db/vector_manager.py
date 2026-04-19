"""
Chroma 向量数据库管理模块
负责知识库的向量存储和语义搜索功能。
采用延迟初始化策略，首次使用时才加载数据库连接和嵌入模型。
"""
import os
from config.settings import settings


class VectorManager:
    """
    向量数据库管理器
    - 封装 Chroma 的初始化、数据写入和语义搜索操作
    - 延迟加载数据库实例，避免模块导入时的性能开销
    """

    def __init__(self, persist_directory: str = None):
        self.persist_directory = persist_directory or settings.VECTOR_DB_PATH
        self._client = None
        self._collections = {}

    def _get_client(self):
        if self._client is None:
            import chromadb
            from chromadb.utils import embedding_functions
            os.makedirs(self.persist_directory, exist_ok=True)
            self._embedding_fn = embedding_functions.HuggingFaceEmbeddingFunction(
                model_name="BAAI/bge-small-zh-v1.5",
            )
            self._client = chromadb.PersistentClient(path=self.persist_directory)
        return self._client

    def _get_collection(self, table_name: str):
        if table_name not in self._collections:
            client = self._get_client()
            self._collections[table_name] = client.get_or_create_collection(
                name=table_name,
                embedding_function=self._embedding_fn,
            )
        return self._collections[table_name]

    def init_table(self, table_name: str = "knowledge_chunks"):
        self._get_collection(table_name)

    def insert_records(self, table_name: str, records: list[dict]):
        collection = self._get_collection(table_name)
        ids = [r["chunk_id"] for r in records]
        documents = [r["content"] for r in records]
        metadatas = [
            {"doc_id": r["doc_id"], "title": r["title"], "metadata": r.get("metadata", "")}
            for r in records
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    def search(self, table_name: str, query_text: str, limit: int = None) -> list[dict]:
        limit = limit or settings.VECTOR_SEARCH_LIMIT
        collection = self._get_collection(table_name)
        results = collection.query(query_texts=[query_text], n_results=limit)

        records = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                records.append({
                    "title": meta.get("title", ""),
                    "content": doc,
                    "doc_id": meta.get("doc_id", ""),
                })
        return records

    def delete_by_doc_id(self, table_name: str, doc_id: str):
        collection = self._get_collection(table_name)
        collection.delete(where={"doc_id": doc_id})


vector_manager = VectorManager()
