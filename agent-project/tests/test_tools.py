import pytest


class TestTools:
    """工具模块单元测试"""

    def test_calculate_valid(self):
        from tools.calculator_tool import calculate
        result = calculate.invoke({"expression": "2 + 3 * 4"})
        assert "14" in result

    def test_calculate_invalid(self):
        from tools.calculator_tool import calculate
        result = calculate.invoke({"expression": "import os"})
        assert "错误" in result

    def test_get_time(self):
        from tools.time_tool import get_current_time
        result = get_current_time.invoke({})
        assert "当前时间" in result
