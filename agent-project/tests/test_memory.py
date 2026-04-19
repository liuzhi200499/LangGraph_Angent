import pytest
import os
import tempfile


class TestMemory:
    """记忆管理单元测试"""

    def setup_method(self):
        self.db_path = os.path.join(tempfile.gettempdir(), "test_agent.db")
        from db.sqlite_manager import SQLiteManager
        self.manager = SQLiteManager(db_path=self.db_path)

    def teardown_method(self):
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_save_and_load(self):
        self.manager.save_message("thread_1", "user_1", "user", "你好")
        messages = self.manager.load_messages("thread_1")
        assert len(messages) == 1
        assert messages[0]["content"] == "你好"

    def test_multiple_messages(self):
        self.manager.save_message("thread_1", "user_1", "user", "你好")
        self.manager.save_message("thread_1", "user_1", "assistant", "你好！有什么可以帮助你的？")
        messages = self.manager.load_messages("thread_1")
        assert len(messages) == 2

    def test_different_threads(self):
        self.manager.save_message("thread_a", "user_1", "user", "消息A")
        self.manager.save_message("thread_b", "user_1", "user", "消息B")
        msgs_a = self.manager.load_messages("thread_a")
        msgs_b = self.manager.load_messages("thread_b")
        assert len(msgs_a) == 1
        assert len(msgs_b) == 1
        assert msgs_a[0]["content"] == "消息A"
