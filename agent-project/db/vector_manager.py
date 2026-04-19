import os
import json
from typing import Optional
from config.settings import settings


class VectorManager:
    def __init__(self, persist_directory: str = None, embedding_model: str = None):
        self.persist_directory = persist_directory or settings.VECTOR_DB_PATH
        self.embedding_model = embedding_model or settings.EMBEDDING_MODEL
        self._db = None

    def _get_db(self):
        if self._db is None:
            from menteedb import MenteeDB
            os.makedirs(self.persist_directory, exist_ok=True)
            self._db = MenteeDB(
                persist_directory=self.persist_directory,
                embedding_model=self.embedding_model,
            )
        return self._db

    def init_table(self, table_name: str = "knowledge_chunks"):
        db = self._get_db()
        db.create_table(
            table_name=table_name,
            fields=["doc_id", "chunk_id", "title", "content", "metadata"],
        )

    def insert_records(self, table_name: str, records: list[dict]):
        db = self._get_db()
        db.batch_insert(table_name, records)

    def search(self, table_name: str, query_text: str, limit: int = None) -> list[dict]:
        limit = limit or settings.VECTOR_SEARCH_LIMIT
        db = self._get_db()
        return db.search(
            table_name=table_name,
            query_text=query_text,
            limit=limit,
        )

    def delete_by_doc_id(self, table_name: str, doc_id: str):
        db = self._get_db()
        db.delete(table_name, filters={"doc_id": doc_id})


vector_manager = VectorManager()
