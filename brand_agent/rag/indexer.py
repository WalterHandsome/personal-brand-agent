"""文档索引 - 将笔记导入向量数据库"""

from pathlib import Path


def build_index(notes_dir: str) -> int:
    """构建 RAG 索引

    将指定目录下的 Markdown 笔记导入 ChromaDB 向量数据库。

    Args:
        notes_dir: 笔记目录路径

    Returns:
        索引的文档数量
    """
    notes_path = Path(notes_dir)
    if not notes_path.exists():
        print(f"⚠️ 目录不存在: {notes_dir}")
        return 0

    # 收集所有 Markdown 文件
    md_files = list(notes_path.rglob("*.md"))
    if not md_files:
        print(f"⚠️ 未找到 Markdown 文件: {notes_dir}")
        return 0

    print(f"📄 找到 {len(md_files)} 个 Markdown 文件")

    # TODO: 完整实现
    # 1. 用 LangChain DirectoryLoader 加载文档
    # 2. 用 RecursiveCharacterTextSplitter 分块
    # 3. 用 OpenAI/Anthropic Embeddings 向量化
    # 4. 存入 ChromaDB

    # from langchain_community.document_loaders import DirectoryLoader
    # from langchain.text_splitter import RecursiveCharacterTextSplitter
    # from langchain_openai import OpenAIEmbeddings
    # from langchain_chroma import Chroma
    #
    # loader = DirectoryLoader(notes_dir, glob="**/*.md")
    # docs = loader.load()
    #
    # splitter = RecursiveCharacterTextSplitter(
    #     chunk_size=1000,
    #     chunk_overlap=200,
    # )
    # chunks = splitter.split_documents(docs)
    #
    # vectorstore = Chroma.from_documents(
    #     documents=chunks,
    #     embedding=OpenAIEmbeddings(),
    #     persist_directory=settings.chroma_persist_dir,
    # )

    return len(md_files)
