"""
知识库数据导入脚本
支持从文件或命令行直接导入知识文本到向量数据库。
运行命令示例：
  python scripts/import_data.py --title "文档标题" --file data.txt
  python scripts/import_data.py --title "文档标题" --text "直接传入的文本内容"
"""
import argparse
from services.knowledge_service import import_knowledge, get_knowledge_stats


def main():
    # 定义命令行参数
    parser = argparse.ArgumentParser(description="知识库数据导入工具")
    parser.add_argument("--title", required=True, help="文档标题")
    parser.add_argument("--file", help="文本文件路径（与 --text 二选一）")
    parser.add_argument("--text", help="直接传入文本内容（与 --file 二选一）")
    parser.add_argument("--source", default="cli", help="来源标记，默认为 cli")
    args = parser.parse_args()

    # 从文件读取或直接使用命令行文本
    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    elif args.text:
        content = args.text
    else:
        print("请指定 --file 或 --text 参数")
        return

    # 执行导入
    doc_id, chunk_count = import_knowledge(args.title, content, args.source)
    print(f"导入成功！")
    print(f"  文档ID: {doc_id}")
    print(f"  分块数: {chunk_count}")

    # 显示当前知识库统计信息
    stats = get_knowledge_stats()
    print(f"\n知识库统计:")
    print(f"  文档总数: {stats['document_count']}")
    print(f"  知识分块: {stats['total_chunks']}")


if __name__ == "__main__":
    main()
