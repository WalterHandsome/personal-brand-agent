"""信息采集 Agent - 每日自动采集 AI 领域热点"""

import httpx
import feedparser
from typing import TypedDict
from langgraph.graph import StateGraph, END


class CollectorState(TypedDict):
    """采集 Agent 的状态"""
    sources: list[str]          # 要采集的信息源
    raw_items: list[dict]       # 原始采集结果
    ranked_items: list[dict]    # 排序后的结果
    daily_brief: str            # 每日简报


def fetch_hackernews(state: CollectorState) -> CollectorState:
    """从 Hacker News 采集 AI 相关热帖"""
    url = "https://hacker-news.firebaseio.com/v0/topstories.json"
    try:
        resp = httpx.get(url, timeout=10)
        story_ids = resp.json()[:30]  # 取前 30 条

        items = []
        for sid in story_ids[:10]:  # 详细获取前 10 条
            story = httpx.get(
                f"https://hacker-news.firebaseio.com/v0/item/{sid}.json",
                timeout=5,
            ).json()
            if story and any(
                kw in (story.get("title", "")).lower()
                for kw in ["ai", "agent", "llm", "gpt", "claude", "rag", "mcp"]
            ):
                items.append({
                    "source": "Hacker News",
                    "title": story.get("title", ""),
                    "url": story.get("url", ""),
                    "score": str(story.get("score", 0)),
                })
    except Exception:
        items = []

    state["raw_items"].extend(items)
    return state


def fetch_github_trending(state: CollectorState) -> CollectorState:
    """从 GitHub Trending 采集热门 AI 项目"""
    # TODO: 通过 GitHub API 或 MCP Server 获取 trending 项目
    # 这里是骨架实现
    state["raw_items"].extend([])
    return state


def rank_and_filter(state: CollectorState) -> CollectorState:
    """对采集结果排序和过滤"""
    # 按热度排序，去重
    seen = set()
    ranked = []
    for item in sorted(state["raw_items"], key=lambda x: int(x.get("score", 0)), reverse=True):
        if item["title"] not in seen:
            seen.add(item["title"])
            ranked.append(item)
    state["ranked_items"] = ranked[:20]  # 保留 Top 20
    return state


def generate_brief(state: CollectorState) -> CollectorState:
    """用 LLM 生成每日简报"""
    # TODO: 调用 LLM 生成结构化简报
    items_text = "\n".join(
        f"- [{item['source']}] {item['title']}" for item in state["ranked_items"]
    )
    state["daily_brief"] = f"📡 今日 AI 热点 Top {len(state['ranked_items'])}：\n\n{items_text}"
    return state


# 构建采集工作流图
def build_collector_graph():
    """构建信息采集 Agent 的 LangGraph 工作流"""
    graph = StateGraph(CollectorState)

    graph.add_node("fetch_hn", fetch_hackernews)
    graph.add_node("fetch_github", fetch_github_trending)
    graph.add_node("rank", rank_and_filter)
    graph.add_node("brief", generate_brief)

    graph.set_entry_point("fetch_hn")
    graph.add_edge("fetch_hn", "fetch_github")
    graph.add_edge("fetch_github", "rank")
    graph.add_edge("rank", "brief")
    graph.add_edge("brief", END)

    return graph.compile()


def collect_trending() -> list[dict]:
    """CLI 调用入口：获取今日热点"""
    workflow = build_collector_graph()
    result = workflow.invoke({
        "sources": ["hackernews", "github"],
        "raw_items": [],
        "ranked_items": [],
        "daily_brief": "",
    })
    return result["ranked_items"]
