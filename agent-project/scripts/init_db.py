"""
数据库初始化脚本
在项目首次运行前执行，创建 SQLite 表结构和 MenteeDB 向量表。
运行命令：python scripts/init_db.py
"""
from db.sqlite_manager import SQLiteManager
from db.vector_manager import VectorManager
from config.settings import settings


def main():
    # 初始化 SQLite 关系数据库（创建 conversations / knowledge_documents / system_configs 表）
    print("正在初始化 SQLite 数据库...")
    SQLiteManager()
    print("SQLite 数据库初始化完成。")

    # 初始化 MenteeDB 向量数据库（创建 knowledge_chunks 向量表并加载嵌入模型）
    print("正在初始化 MenteeDB 向量数据库...")
    vm = VectorManager()
    vm.init_table("knowledge_chunks")
    print("MenteeDB 向量数据库初始化完成。")

    print("所有数据库初始化完成！")


if __name__ == "__main__":
    main()
