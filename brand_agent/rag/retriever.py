"""检索器 - 从向量数据库检索相关内容"""


def search(query: str, top_k: int = 5) -> list[dict]:
    """从知识库检索与查询相关的内容

    Args:
        query: 检索查询
        top_k: 返回结果数量

    Returns:
        检索结果列表，每个结果包含 source 和 content
    """
    # TODO: 完整实现
    # from langchain_chroma import Chroma
    # from langchain_openai import OpenAIEmbeddings
    # from brand_agent.config import settings
    #
    # vectorstore = Chroma(
    #     persist_directory=settings.chroma_persist_dir,
    #     embedding_function=OpenAIEmbeddings(),
    # )
    # retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})
    # docs = retriever.invoke(query)
    #
    # return [
    #     {"source": doc.metadata.get("source", "unknown"), "content": doc.page_content}
    #     for doc in docs
    # ]

    return [
        {
            "source": "placeholder",
            "content": f"[知识库检索结果占位 - 查询: {query}]",
        }
    ]
