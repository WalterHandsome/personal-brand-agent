"""内容生成 Agent - 基于知识库生成高质量技术文章"""

import json
from datetime import date
from pathlib import Path
from typing import TypedDict
from langgraph.graph import StateGraph, END


class WriterState(TypedDict):
    """写作 Agent 的状态"""
    topic: str                  # 文章主题
    style: str                  # 输出风格
    retrieved_context: str      # RAG 检索到的相关内容
    outline: str                # 文章大纲
    draft: str                  # 初稿
    final_article: dict         # 最终文章对象
    saved_path: str             # 保存路径


def retrieve_knowledge(state: WriterState) -> WriterState:
    """从知识库检索与主题相关的内容"""
    from brand_agent.rag.retriever import search

    results = search(state["topic"], top_k=5)
    state["retrieved_context"] = "\n\n---\n\n".join(
        f"[{r['source']}]\n{r['content']}" for r in results
    )
    return state


def generate_outline(state: WriterState) -> WriterState:
    """用 LLM 生成文章大纲"""
    # TODO: 调用 LLM 生成大纲
    # 骨架实现：基于主题生成默认大纲
    state["outline"] = f"""
# {state['topic']}

## 引言
## 核心概念
## 实战示例
## 最佳实践
## 总结
"""
    return state


def write_draft(state: WriterState) -> WriterState:
    """基于大纲和检索内容生成初稿"""
    # TODO: 调用 LLM，传入大纲 + 检索内容，生成完整文章
    state["draft"] = f"[基于 RAG 知识库生成的 {state['topic']} 文章初稿]"
    return state


def format_output(state: WriterState) -> WriterState:
    """根据目标风格格式化输出"""
    today = date.today().isoformat()
    article = {
        "id": state["topic"].lower().replace(" ", "-").replace("：", "-"),
        "title": state["topic"],
        "date": today,
        "tags": [],  # TODO: LLM 自动生成标签
        "excerpt": "",  # TODO: LLM 生成摘要
        "body": state["draft"],
    }

    # 保存到本地
    save_dir = Path("data/articles")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{today}-{article['id']}.json"
    save_path.write_text(json.dumps(article, ensure_ascii=False, indent=2))

    state["final_article"] = article
    state["saved_path"] = str(save_path)
    return state


# 构建写作工作流图
def build_writer_graph():
    """构建内容生成 Agent 的 LangGraph 工作流"""
    graph = StateGraph(WriterState)

    graph.add_node("retrieve", retrieve_knowledge)
    graph.add_node("outline", generate_outline)
    graph.add_node("write", write_draft)
    graph.add_node("format", format_output)

    graph.set_entry_point("retrieve")
    graph.add_edge("retrieve", "outline")
    graph.add_edge("outline", "write")
    graph.add_edge("write", "format")
    graph.add_edge("format", END)

    return graph.compile()


def generate_article(topic: str, style: str = "blog") -> dict:
    """CLI 调用入口：生成文章"""
    workflow = build_writer_graph()
    result = workflow.invoke({
        "topic": topic,
        "style": style,
        "retrieved_context": "",
        "outline": "",
        "draft": "",
        "final_article": {},
        "saved_path": "",
    })
    return result["final_article"] | {"saved_path": result["saved_path"]}
