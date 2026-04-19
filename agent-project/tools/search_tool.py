import json
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from db.vector_manager import vector_manager


class SearchInput(BaseModel):
    query: str = Field(description="搜索查询文本")
    top_k: int = Field(default=5, description="返回结果数量")


def format_search_results(results: list) -> str:
    if not results:
        return "未找到相关内容。"
    formatted = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "未知")
        content = r.get("content", "")
        formatted.append(f"[{i}] {title}\n{content}")
    return "\n\n".join(formatted)


@tool(args_schema=SearchInput)
def search_knowledge_base(query: str, top_k: int = 5) -> str:
    """在知识库中进行语义搜索，返回与查询最相关的知识片段。"""
    results = vector_manager.search(
        table_name="knowledge_chunks",
        query_text=query,
        limit=top_k,
    )
    return format_search_results(results)
