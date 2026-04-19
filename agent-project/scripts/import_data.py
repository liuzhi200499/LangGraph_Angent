"""导入知识数据"""
import argparse
from services.knowledge_service import import_knowledge, get_knowledge_stats


def main():
    parser = argparse.ArgumentParser(description="知识库数据导入工具")
    parser.add_argument("--title", required=True, help="文档标题")
    parser.add_argument("--file", help="文本文件路径")
    parser.add_argument("--text", help="直接传入文本内容")
    parser.add_argument("--source", default="cli", help="来源标记")
    args = parser.parse_args()

    if args.file:
        with open(args.file, "r", encoding="utf-8") as f:
            content = f.read()
    elif args.text:
        content = args.text
    else:
        print("请指定 --file 或 --text 参数")
        return

    doc_id, chunk_count = import_knowledge(args.title, content, args.source)
    print(f"导入成功！")
    print(f"  文档ID: {doc_id}")
    print(f"  分块数: {chunk_count}")

    stats = get_knowledge_stats()
    print(f"\n知识库统计:")
    print(f"  文档总数: {stats['document_count']}")
    print(f"  知识分块: {stats['total_chunks']}")


if __name__ == "__main__":
    main()
