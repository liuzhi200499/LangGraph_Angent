"""
计算器工具
Agent 可调用的工具之一，执行基本数学运算。
通过白名单字符过滤，防止代码注入攻击。
"""
from langchain_core.tools import tool


@tool
def calculate(expression: str) -> str:
    """
    执行数学计算表达式。
    安全机制：仅允许数字和基本运算符 (+, -, *, /, %, 括号)，
    阻止任何可能执行恶意代码的输入（如 import、__ 等）。
    """
    # 白名单字符集，防止 eval() 执行恶意代码
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        return "错误：表达式包含非法字符"
    try:
        result = eval(expression)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算错误：{e}"
