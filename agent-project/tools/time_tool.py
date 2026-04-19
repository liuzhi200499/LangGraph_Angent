"""
时间查询工具
Agent 可调用的工具之一，返回当前系统的日期和时间。
"""
from langchain_core.tools import tool
from datetime import datetime


@tool
def get_current_time() -> str:
    """获取当前系统的日期和时间，格式为 YYYY-MM-DD HH:MM:SS"""
    return f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
