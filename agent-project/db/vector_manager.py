"""
MenteeDB 向量数据库管理模块
负责知识库的向量存储和语义搜索功能。
采用延迟初始化策略，首次使用时才加载嵌入模型和数据库连接。
"""
import os
import json
from typing import Optional
from config.settings import settings


class VectorManager:
    """
    向量数据库管理器
    - 封装 MenteeDB 的初始化、数据写入和语义搜索操作
    - 延迟加载数据库实例，避免模块导入时的性能开销
    """

    def __init__(self, persist_directory: str = None, embedding_model: str = None):
        self.persist_directory = persist_directory or settings.VECTOR_DB_PATH
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self._db = None  # 延迟初始化，首次调用 _get_db() 时才创建实例

    def _get_db(self):
        """延迟初始化并返回 MenteeDB 实例，自动创建持久化目录"""
        if self._db is None:
            from menteedb import MenteeDB
            os.makedirs(self.persist_directory, exist_ok=True)
            self._db = MenteeDB(
                persist_directory=self.persist_directory,
                embedding_model=self.embedding_model,  # 加载 Sentence-Transformers 嵌入模型
            )
        return self._db

    def init_table(self, table_name: str = "knowledge_chunks"):
        """创建向量表，定义文档、分块、标题、内容和元数据字段"""
        db = self._get_db()
        db.create_table(
            table_name=table_name,
            fields=["doc_id", "chunk_id", "title", "content", "metadata"],
            # content 字段会自动进行向量化和索引
        )

    def insert_records(self, table_name: str, records: list[dict]):
        """批量插入向量化记录到指定表中"""
        db = self._get_db()
        db.batch_insert(table_name, records)

    def search(self, table_name: str, query_text: str, limit: int = None) -> list[dict]:
        """
        语义搜索：将查询文本向量化后，在向量库中查找最相似的记录
        - query_text: 用户的自然语言查询
        - limit: 返回结果数量上限
        """
        limit = limit or settings.VECTOR_SEARCH_LIMIT
        db = self._get_db()
        return db.search(
            table_name=table_name,
            query_text=query_text,
            limit=limit,
        )

    def delete_by_doc_id(self, table_name: str, doc_id: str):
        """根据文档 ID 删除该文档关联的所有向量记录"""
        db = self._get_db()
        db.delete(table_name, filters={"doc_id": doc_id})


# 全局单例，供其他模块直接导入使用
vector_manager = VectorManager()
