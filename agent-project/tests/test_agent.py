import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage


class TestAgentCore:
    """Agent 核心逻辑单元测试"""

    @patch("core.agent.completion")
    def test_direct_response(self, mock_llm):
        """测试 Agent 直接回答（不调用工具）"""
        mock_msg = MagicMock()
        mock_msg.content = "这是回答"
        mock_msg.tool_calls = None
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )
        from core.agent import agent_node
        result = agent_node({"messages": [HumanMessage(content="你好")]})
        assert result["messages"][0].content == "这是回答"

    @patch("core.agent.completion")
    def test_tool_call(self, mock_llm):
        """测试 Agent 触发工具调用"""
        mock_tool_call = MagicMock()
        mock_tool_call.function.name = "get_current_time"
        mock_tool_call.function.arguments = "{}"
        mock_msg = MagicMock()
        mock_msg.content = None
        mock_msg.tool_calls = [mock_tool_call]
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )
        from core.agent import agent_node
        result = agent_node({"messages": [HumanMessage(content="几点了")]})
        assert result["messages"][0].tool_calls is not None
