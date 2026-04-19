from langchain_core.tools import tool


@tool
def calculate(expression: str) -> str:
    """执行数学计算表达式。仅支持数字和基本运算符 (+, -, *, /, %, 括号)。"""
    allowed = set("0123456789+-*/().% ")
    if not all(c in allowed for c in expression):
        return "错误：表达式包含非法字符"
    try:
        result = eval(expression)
        return f"计算结果：{result}"
    except Exception as e:
        return f"计算错误：{e}"
