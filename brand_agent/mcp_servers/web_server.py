"""Web 采集 MCP Server - 提供网页内容抓取和热点采集工具"""

# 使用方式：
# 1. 直接运行：python -m brand_agent.mcp_servers.web_server
# 2. 配置到 Kiro/Claude Desktop 的 mcp.json 中

from mcp.server.fastmcp import FastMCP
import httpx
import feedparser

mcp = FastMCP("brand-web-tools")


@mcp.tool()
def fetch_hackernews_ai(limit: int = 10) -> str:
    """获取 Hacker News 上与 AI 相关的热门帖子

    Args:
        limit: 返回结果数量，默认 10
    """
    keywords = ["ai", "agent", "llm", "gpt", "claude", "rag", "mcp", "langchain"]

    resp = httpx.get(
        "https://hacker-news.firebaseio.com/v0/topstories.json", timeout=10
    )
    story_ids = resp.json()[:50]

    results = []
    for sid in story_ids:
        if len(results) >= limit:
            break
        story = httpx.get(
            f"https://hacker-news.firebaseio.com/v0/item/{sid}.json", timeout=5
        ).json()
        if story and any(kw in story.get("title", "").lower() for kw in keywords):
            results.append(
                f"- [{story['title']}]({story.get('url', '')}) (score: {story.get('score', 0)})"
            )

    return "\n".join(results) if results else "今日暂无 AI 相关热帖"


@mcp.tool()
def fetch_rss_feed(url: str, limit: int = 10) -> str:
    """获取 RSS 订阅源的最新内容

    Args:
        url: RSS 订阅源 URL
        limit: 返回条目数量
    """
    feed = feedparser.parse(url)
    entries = feed.entries[:limit]

    results = []
    for entry in entries:
        title = entry.get("title", "无标题")
        link = entry.get("link", "")
        published = entry.get("published", "")
        results.append(f"- [{title}]({link}) ({published})")

    return "\n".join(results) if results else "未获取到内容"


@mcp.tool()
def fetch_webpage_content(url: str) -> str:
    """获取网页的文本内容（去除 HTML 标签）

    Args:
        url: 网页 URL
    """
    import re

    resp = httpx.get(url, timeout=15, follow_redirects=True)
    # 简单的 HTML 标签清理
    text = re.sub(r"<[^>]+>", "", resp.text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:5000]  # 限制返回长度


if __name__ == "__main__":
    mcp.run()
