"""多平台分发 Agent - 通过 Postiz 将文章发布到多个社交平台

支持的平台（取决于你在 Postiz 中绑定了哪些账号）：
- x (Twitter/X)
- linkedin / linkedin-page
- bluesky, threads, mastodon
- medium, devto, hashnode, wordpress
- reddit, facebook, instagram
- 等 28+ 平台

工作流：加载文章 → 适配各平台内容格式 → 通过 Postiz API 发布
"""

import json
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, END


# ============================================
# Postiz 平台标识 → 内容适配规则
# ============================================

# 短内容平台（有字数限制，需要精简）
SHORT_CONTENT_PLATFORMS = {"x", "threads", "bluesky", "mastodon"}
# 长内容/博客平台（支持 Markdown 或富文本）
LONG_CONTENT_PLATFORMS = {"medium", "devto", "hashnode", "wordpress", "linkedin", "linkedin-page", "reddit"}
# 其他平台
OTHER_PLATFORMS = {"facebook", "instagram", "telegram", "discord"}


class DistributorState(TypedDict):
    """分发 Agent 的状态"""
    article_id: str
    article: dict
    platforms: list[str]           # Postiz 平台标识列表
    adapted_content: dict          # 平台 -> 适配后的内容（str 或 list[str]）
    results: dict[str, dict]       # 平台 -> 发布结果


# ============================================
# 工作流节点
# ============================================

def load_article(state: DistributorState) -> DistributorState:
    """加载待分发的文章"""
    if state["article_id"] == "latest":
        articles_dir = Path("data/articles")
        if articles_dir.exists():
            files = sorted(articles_dir.glob("*.json"), reverse=True)
            if files:
                state["article"] = json.loads(files[0].read_text(encoding="utf-8"))
                return state

    # 按 ID 查找
    article_path = Path(f"data/articles/{state['article_id']}.json")
    if article_path.exists():
        state["article"] = json.loads(article_path.read_text(encoding="utf-8"))
        return state

    state["article"] = {}
    return state


def adapt_content(state: DistributorState) -> DistributorState:
    """根据目标平台适配内容格式"""
    article = state["article"]
    if not article:
        return state

    title = article.get("title", "")
    body = article.get("body", "")
    excerpt = article.get("excerpt", "")
    tags = article.get("tags", [])
    tag_str = " ".join(f"#{t}" for t in tags[:5]) if tags else ""

    adapted = {}
    for platform in state["platforms"]:
        if platform == "x":
            # Twitter/X：拆分为 Thread，每条 ≤280 字符
            adapted[platform] = _adapt_for_x(title, excerpt, body, tag_str)
        elif platform in SHORT_CONTENT_PLATFORMS:
            # 短内容平台：标题 + 摘要 + 标签
            text = f"{title}\n\n{excerpt}"
            if tag_str:
                text += f"\n\n{tag_str}"
            adapted[platform] = text[:500]
        elif platform in LONG_CONTENT_PLATFORMS:
            # 长内容平台：完整 Markdown
            content = f"# {title}\n\n{body}"
            if tag_str:
                content += f"\n\n---\n{tag_str}"
            adapted[platform] = content
        else:
            # 其他平台：标题 + 摘要
            adapted[platform] = f"{title}\n\n{excerpt}"

    state["adapted_content"] = adapted
    return state


def _adapt_for_x(title: str, excerpt: str, body: str, tag_str: str) -> list[str]:
    """将文章适配为 Twitter/X Thread 格式"""
    tweets = []

    # 第一条：标题 + 摘要
    first = f"🧵 {title}\n\n{excerpt}"
    if len(first) > 280:
        first = first[:277] + "..."
    tweets.append(first)

    # 中间：按段落拆分正文
    paragraphs = [p.strip() for p in body.split("\n\n") if p.strip()]
    current = ""
    for para in paragraphs:
        # 跳过 HTML 标签和标题标记
        if para.startswith("<") or para.startswith("#"):
            clean = para.lstrip("#").strip()
            if not clean:
                continue
            para = clean

        if len(current) + len(para) + 2 <= 270:
            current = f"{current}\n\n{para}" if current else para
        else:
            if current:
                tweets.append(current)
            current = para[:270]

        # 最多 6 条 Thread
        if len(tweets) >= 5:
            break

    if current:
        tweets.append(current)

    # 最后一条：标签 + CTA
    if tag_str:
        tweets.append(f"{tag_str}\n\n💬 你怎么看？欢迎讨论")

    return tweets


def publish_to_platforms(state: DistributorState) -> DistributorState:
    """通过 Postiz API 发布到各平台"""
    from brand_agent.config import settings

    if not settings.postiz_url or not settings.postiz_api_key:
        # Postiz 未配置，返回提示
        state["results"] = {
            p: {"success": False, "message": "Postiz 未配置，请设置 POSTIZ_URL 和 POSTIZ_API_KEY"}
            for p in state["platforms"]
        }
        return state

    from brand_agent.platforms.postiz import PostizClient
    client = PostizClient(settings.postiz_url, settings.postiz_api_key)

    results = {}
    for platform in state["platforms"]:
        content = state["adapted_content"].get(platform)
        if not content:
            results[platform] = {"success": False, "message": "无适配内容"}
            continue

        try:
            # X/Twitter 的特殊设置
            platform_settings = None
            if platform == "x":
                platform_settings = {
                    "__type": "x",
                    "who_can_reply_post": "everyone",
                    "made_with_ai": False,
                }

            result = client.publish_now(
                provider=platform,
                content=content,
                settings=platform_settings,
            )
            results[platform] = {
                "success": True,
                "message": f"已发布到 {platform}",
                "post_id": result[0].get("postId") if isinstance(result, list) else None,
            }
        except ValueError as e:
            # 未绑定该平台
            results[platform] = {"success": False, "message": str(e)}
        except Exception as e:
            results[platform] = {"success": False, "message": f"发布失败: {e}"}

    state["results"] = results
    return state


# ============================================
# 构建工作流
# ============================================

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
    """CLI 调用入口：分发文章到指定平台"""
    workflow = build_distributor_graph()
    result = workflow.invoke({
        "article_id": article_id,
        "article": {},
        "platforms": platforms,
        "adapted_content": {},
        "results": {},
    })
    return result["results"]


def list_channels() -> list[dict]:
    """列出 Postiz 中已连接的所有平台账号"""
    from brand_agent.config import settings

    if not settings.postiz_url or not settings.postiz_api_key:
        return []

    from brand_agent.platforms.postiz import PostizClient
    client = PostizClient(settings.postiz_url, settings.postiz_api_key)
    return client.list_integrations()
