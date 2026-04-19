"""
SQLite 对话记忆管理单元测试
使用临时数据库文件进行测试，每个测试方法结束后自动清理。
验证消息的保存、加载和多会话隔离功能。
"""
import pytest
import os
import tempfile


class TestMemory:
    """记忆管理单元测试"""

    def setup_method(self):
        """每个测试方法执行前：创建临时数据库文件路径并初始化管理器"""
        self.db_path = os.path.join(tempfile.gettempdir(), "test_agent.db")
        from db.sqlite_manager import SQLiteManager
        self.manager = SQLiteManager(db_path=self.db_path)

    def teardown_method(self):
        """每个测试方法执行后：删除临时数据库文件"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_and_load(self):
        """测试单条消息的保存和加载"""
        self.manager.save_message("thread_1", "user_1", "user", "你好")
        messages = self.manager.load_messages("thread_1")
        assert len(messages) == 1
        assert messages[0]["content"] == "你好"

    def test_multiple_messages(self):
        """测试同一会话中多条消息的保存和按序加载"""
        self.manager.save_message("thread_1", "user_1", "user", "你好")
        self.manager.save_message("thread_1", "user_1", "assistant", "你好！有什么可以帮助你的？")
        messages = self.manager.load_messages("thread_1")
        assert len(messages) == 2  # 应包含一问一答两条消息

    def test_different_threads(self):
        """测试不同会话线程之间的消息隔离性"""
        self.manager.save_message("thread_a", "user_1", "user", "消息A")
        self.manager.save_message("thread_b", "user_1", "user", "消息B")

        msgs_a = self.manager.load_messages("thread_a")
        msgs_b = self.manager.load_messages("thread_b")

        # 各线程应只包含自己的消息，互不干扰
        assert len(msgs_a) == 1
        assert len(msgs_b) == 1
        assert msgs_a[0]["content"] == "消息A"
