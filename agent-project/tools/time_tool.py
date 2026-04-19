from langchain_core.tools import tool
from datetime import datetime


@tool
def get_current_time() -> str:
    """获取当前日期和时间。"""
    return f"当前时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
