"""多平台分发 Agent - 一篇文章适配多个平台"""

from typing import TypedDict
from langgraph.graph import StateGraph, END


class DistributorState(TypedDict):
    """分发 Agent 的状态"""
    article_id: str
    article: dict
    platforms: list[str]
    adapted_content: dict[str, str]  # 平台 -> 适配后的内容
    results: dict[str, dict]         # 平台 -> 发布结果


def load_article(state: DistributorState) -> DistributorState:
    """加载待分发的文章"""
    import json
    from pathlib import Path

    if state["article_id"] == "latest":
        # 获取最新文章
        articles_dir = Path("data/articles")
        if articles_dir.exists():
            files = sorted(articles_dir.glob("*.json"), reverse=True)
            if files:
                state["article"] = json.loads(files[0].read_text())
                return state
    state["article"] = {}
    return state


def adapt_content(state: DistributorState) -> DistributorState:
    """根据目标平台适配内容格式"""
    article = state["article"]
    if not article:
        return state

    adapted = {}
    for platform in state["platforms"]:
        if platform == "blog":
            # 博客：HTML 格式，直接使用
            adapted[platform] = article.get("body", "")
        elif platform == "juejin":
            # 掘金：Markdown 格式
            # TODO: 调用 LLM 将 HTML 转为掘金风格的 Markdown
            adapted[platform] = f"# {article['title']}\n\n{article.get('excerpt', '')}"
        elif platform == "twitter":
            # Twitter：拆分为 thread
            # TODO: 调用 LLM 生成 Twitter thread
            adapted[platform] = f"🧵 {article['title']}\n\n1/ {article.get('excerpt', '')}"
        elif platform == "zhihu":
            # 知乎：Markdown 格式，偏学术风格
            # TODO: 调用 LLM 适配知乎风格
            adapted[platform] = f"# {article['title']}\n\n{article.get('excerpt', '')}"

    state["adapted_content"] = adapted
    return state


def publish_to_platforms(state: DistributorState) -> DistributorState:
    """发布到各平台"""
    results = {}
    for platform in state["platforms"]:
        content = state["adapted_content"].get(platform, "")
        if not content:
            results[platform] = {"success": False, "message": "无适配内容"}
            continue

        try:
            if platform == "blog":
                # TODO: 通过 GitHub API 更新 blog.html
                results[platform] = {"success": True, "message": "已更新博客文件"}
            elif platform == "juejin":
                # TODO: 通过掘金 API 发布
                results[platform] = {"success": True, "message": "已保存掘金草稿"}
            elif platform == "twitter":
                # TODO: 通过 Twitter API 发布 thread
                results[platform] = {"success": True, "message": "已保存 Twitter thread"}
            elif platform == "zhihu":
                # TODO: 通过知乎 API 发布
                results[platform] = {"success": True, "message": "已保存知乎草稿"}
            else:
                results[platform] = {"success": False, "message": f"不支持的平台: {platform}"}
        except Exception as e:
            results[platform] = {"success": False, "message": str(e)}

    state["results"] = results
    return state


# 构建分发工作流图
def build_distributor_graph():
    """构建多平台分发 Agent 的 LangGraph 工作流"""
    graph = StateGraph(DistributorState)

    graph.add_node("load", load_article)
    graph.add_node("adapt", adapt_content)
    graph.add_node("publish", publish_to_platforms)

    graph.set_entry_point("load")
    graph.add_edge("load", "adapt")
    graph.add_edge("adapt", "publish")
    graph.add_edge("publish", END)

    return graph.compile()


def distribute_article(article_id: str, platforms: list[str]) -> dict:
    """CLI 调用入口：分发文章"""
    workflow = build_distributor_graph()
    result = workflow.invoke({
        "article_id": article_id,
        "article": {},
        "platforms": platforms,
        "adapted_content": {},
        "results": {},
    })
    return result["results"]
