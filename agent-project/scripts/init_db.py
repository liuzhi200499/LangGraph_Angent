"""初始化数据库"""
from db.sqlite_manager import SQLiteManager
from db.vector_manager import VectorManager
from config.settings import settings


def main():
    print("正在初始化 SQLite 数据库...")
    SQLiteManager()
    print("SQLite 数据库初始化完成。")

    print("正在初始化 MenteeDB 向量数据库...")
    vm = VectorManager()
    vm.init_table("knowledge_chunks")
    print("MenteeDB 向量数据库初始化完成。")

    print("所有数据库初始化完成！")


if __name__ == "__main__":
    main()
