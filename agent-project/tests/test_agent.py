"""
Agent 核心逻辑单元测试
使用 unittest.mock 模拟 LLM 返回，验证 Agent 节点的推理行为：
- 直接回复场景（不调用工具）
- 触发工具调用场景
"""
import pytest
from unittest.mock import patch, MagicMock
from langchain_core.messages import HumanMessage


class TestAgentCore:
    """Agent 核心逻辑单元测试"""

    @patch("core.agent.completion")  # Mock LiteLLM 的 completion 函数
    def test_direct_response(self, mock_llm):
        """测试 Agent 直接回答场景：LLM 不返回 tool_calls，直接给出文本回复"""
        # 构造模拟的 LLM 返回：包含纯文本回复，无工具调用
        mock_msg = MagicMock()
        mock_msg.content = "这是回答"
        mock_msg.tool_calls = None
        mock_llm.return_value = MagicMock(
            choices=[MagicMock(message=mock_msg)]
        )

        from core.agent import agent_node
        result = agent_node({"messages": [HumanMessage(content="你好")]})

        # 验证返回的消息内容与 Mock 设定一致
        assert result["messages"][0].content == "这是回答"

    @patch("core.agent.completion")
    def test_tool_call(self, mock_llm):
        """测试 Agent 触发工具调用场景：LLM 返回 tool_calls，指示执行某个工具"""
        # 构造模拟的工具调用返回
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

        # 验证返回的消息中包含工具调用
        assert result["messages"][0].tool_calls is not None
