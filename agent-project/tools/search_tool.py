"""
知识库语义搜索工具
Agent 可调用的工具之一，通过 ChromaDB 向量数据库进行语义搜索。
使用 Pydantic Schema 定义参数结构，供 LLM 理解工具的使用方式。
"""
import json
from langchain_core.tools import tool
from pydantic import BaseModel, Field
from db.vector_manager import vector_manager


class SearchInput(BaseModel):
    """搜索工具的输入参数模型，LLM 会根据字段描述生成调用参数"""
    query: str = Field(description="搜索查询文本")
    top_k: int = Field(default=5, description="返回结果数量")


def format_search_results(results: list) -> str:
    """
    将搜索结果格式化为 LLM 可理解的文本
    每条结果包含编号、标题和内容，便于 Agent 理解和引用
    """
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
    """
    在知识库中进行语义搜索，返回与查询最相关的知识片段。
    通过向量相似度匹配，而非关键词匹配，能理解语义相近的内容。
    """
    results = vector_manager.search(
        table_name="knowledge_chunks",  # 在知识分块表中搜索
        query_text=query,               # 用户查询文本（会自动向量化）
        limit=top_k,                    # 返回 top_k 个最相似的结果
    )
    return format_search_results(results)
