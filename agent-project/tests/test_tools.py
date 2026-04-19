"""
工具模块单元测试
验证各 Agent 工具的正确性和安全性：
- 计算器工具：合法表达式 / 非法字符拦截
- 时间工具：返回格式验证
"""
import pytest


class TestTools:
    """工具模块单元测试"""

    def test_calculate_valid(self):
        """测试计算器工具：合法数学表达式应返回正确结果"""
        from tools.calculator_tool import calculate
        result = calculate.invoke({"expression": "2 + 3 * 4"})
        assert "14" in result  # 2 + 3*4 = 14

    def test_calculate_invalid(self):
        """测试计算器工具：包含非法字符时应拒绝执行，防止代码注入"""
        from tools.calculator_tool import calculate
        result = calculate.invoke({"expression": "import os"})
        assert "错误" in result  # 应返回错误信息

    def test_get_time(self):
        """测试时间工具：返回值应包含 '当前时间' 字样"""
        from tools.time_tool import get_current_time
        result = get_current_time.invoke({})
        assert "当前时间" in result
