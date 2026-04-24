"""信息采集 Agent - 每日自动采集 AI Agent 领域热点

数据源：
- Hacker News API（实时热帖）
- GitHub API（trending + releases）
- arXiv API（最新论文）
- RSS feeds（官方博客）

工作流：采集 → 去重 → 评分 → 生成简报 → 输出 Markdown
"""

import json
import hashlib
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TypedDict

import feedparser
import httpx
from langgraph.graph import StateGraph, END


# ============================================
# 状态定义
# ============================================

class CollectorState(TypedDict):
    """采集 Agent 的状态"""
    raw_items: list[dict]
    deduped_items: list[dict]
    scored_items: list[dict]
    daily_brief: str
    stats: dict


# ============================================
# 关键词配置
# ============================================

AI_KEYWORDS = [
    "ai agent", "llm agent", "ai coding", "mcp", "a2a protocol",
    "langgraph", "crewai", "openai", "anthropic", "claude",
    "rag", "vector", "embedding", "function calling", "tool use",
    "multi-agent", "context engineering", "prompt engineering",
    "coding agent", "cursor", "copilot", "kiro",
    "ai safety", "ai governance", "agent security",
    "langchain", "autogen", "semantic kernel",
]

RSS_FEEDS = {
    "OpenAI Blog": "https://openai.com/blog/rss.xml",
    "Anthropic News": "https://www.anthropic.com/rss.xml",
    "LangChain Blog": "https://blog.langchain.dev/rss/",
    "Hugging Face Blog": "https://huggingface.co/blog/feed.xml",
}


# ============================================
# 采集节点
# ============================================

def fetch_hackernews(state: CollectorState) -> CollectorState:
    """从 Hacker News Algolia API 采集 AI 相关热帖（单次请求）"""
    items = []
    search_terms = ["AI agent", "LLM", "MCP protocol", "Claude", "coding agent", "LangGraph"]
    cutoff = int((datetime.now(timezone.utc) - timedelta(hours=48)).timestamp())

    for term in search_terms:
        try:
            resp = httpx.get(
                "https://hn.algolia.com/api/v1/search",
                params={
                    "query": term,
                    "tags": "story",
                    "numericFilters": f"created_at_i>{cutoff}",
                    "hitsPerPage": 10,
                },
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            for hit in resp.json().get("hits", []):
                items.append({
                    "source": "hackernews",
                    "title": hit.get("title", ""),
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    "score": hit.get("points", 0),
                    "published": datetime.fromtimestamp(
                        hit.get("created_at_i", 0), tz=timezone.utc
                    ).isoformat(),
                    "summary": "",
                    "tags": [],
                })
        except Exception as e:
            print(f"[HN] 搜索 '{term}' 失败: {e}")

    seen = set()
    unique = []
    for item in sorted(items, key=lambda x: x.get("score", 0), reverse=True):
        if item["title"] not in seen:
            seen.add(item["title"])
            unique.append(item)
    state["raw_items"].extend(unique[:10])
    return state


def fetch_github_trending(state: CollectorState) -> CollectorState:
    """从 GitHub API 搜索近期热门 AI Agent 项目"""
    items = []
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    queries = [
        f"ai agent pushed:>{since} stars:>100",
        f"mcp server pushed:>{since} stars:>50",
        f"llm framework pushed:>{since} stars:>100",
        f"coding agent pushed:>{since} stars:>50",
    ]

    headers = {}
    try:
        from brand_agent.config import settings
        if settings.github_token:
            headers["Authorization"] = f"token {settings.github_token}"
    except Exception:
        pass

    for query in queries:
        try:
            resp = httpx.get(
                "https://api.github.com/search/repositories",
                params={"q": query, "sort": "stars", "order": "desc", "per_page": 10},
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 200:
                continue
            for repo in resp.json().get("items", []):
                items.append({
                    "source": "github",
                    "title": f"{repo['full_name']}: {repo.get('description', '')[:100]}",
                    "url": repo["html_url"],
                    "score": repo.get("stargazers_count", 0),
                    "published": repo.get("pushed_at", ""),
                    "summary": repo.get("description", ""),
                    "tags": repo.get("topics", [])[:5],
                    "language": repo.get("language", ""),
                    "stars": repo.get("stargazers_count", 0),
                })
        except Exception as e:
            print(f"[GitHub] 搜索失败: {e}")

    seen_repos = set()
    unique = []
    for item in sorted(items, key=lambda x: x.get("stars", 0), reverse=True):
        repo_name = item["url"].split("github.com/")[-1] if "github.com/" in item["url"] else ""
        if repo_name not in seen_repos:
            seen_repos.add(repo_name)
            unique.append(item)
    state["raw_items"].extend(unique[:10])
    return state


def fetch_arxiv(state: CollectorState) -> CollectorState:
    """从 arXiv API 采集最新 AI Agent 论文"""
    items = []
    queries = [
        "all:ai+agent+AND+all:llm",
        "all:multi-agent+AND+all:reasoning",
        "all:tool+use+AND+all:language+model",
    ]

    for query in queries:
        try:
            resp = httpx.get(
                "http://export.arxiv.org/api/query",
                params={"search_query": query, "start": 0, "max_results": 5,
                        "sortBy": "submittedDate", "sortOrder": "descending"},
                timeout=15,
            )
            feed = feedparser.parse(resp.text)
            for entry in feed.entries:
                published = entry.get("published", "")
                authors = ", ".join(a.get("name", "") for a in entry.get("authors", [])[:3])
                if len(entry.get("authors", [])) > 3:
                    authors += " 等"
                items.append({
                    "source": "arxiv",
                    "title": entry.get("title", "").replace("\n", " ").strip(),
                    "url": entry.get("link", ""),
                    "score": 0,
                    "published": published,
                    "summary": entry.get("summary", "").replace("\n", " ").strip()[:300],
                    "tags": [t.get("term", "") for t in entry.get("tags", [])[:5]],
                    "authors": authors,
                })
        except Exception as e:
            print(f"[arXiv] 采集失败: {e}")

    seen = set()
    unique = []
    for item in items:
        key = item["title"][:50].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)
    state["raw_items"].extend(unique[:8])
    return state


def fetch_rss_feeds(state: CollectorState) -> CollectorState:
    """从官方博客 RSS 采集最新文章"""
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            resp = httpx.get(feed_url, timeout=5, follow_redirects=True)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:5]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                else:
                    pub_str = ""
                items.append({
                    "source": f"rss:{source_name}",
                    "title": entry.get("title", ""),
                    "url": entry.get("link", ""),
                    "score": 0,
                    "published": pub_str,
                    "summary": entry.get("summary", "")[:300],
                    "tags": [],
                })
        except Exception as e:
            print(f"[RSS:{source_name}] 采集失败: {e}")

    state["raw_items"].extend(items[:10])
    return state


# ============================================
# 去重节点
# ============================================

def _url_hash(url: str) -> str:
    clean = url.split("?")[0].split("#")[0].rstrip("/").lower()
    return hashlib.md5(clean.encode()).hexdigest()[:12]


def _title_similarity(a: str, b: str) -> float:
    words_a = set(re.findall(r'\w+', a.lower()))
    words_b = set(re.findall(r'\w+', b.lower()))
    if not words_a or not words_b:
        return 0.0
    return len(words_a & words_b) / len(words_a | words_b)


def _load_history_titles(days: int = 3) -> list[str]:
    titles = []
    briefings_dir = Path("output/briefings")
    if not briefings_dir.exists():
        return titles
    for i in range(1, days + 1):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = briefings_dir / f"{date_str}.md"
        if filepath.exists():
            for line in filepath.read_text(encoding="utf-8").split("\n"):
                if line.startswith("### "):
                    titles.append(line[4:].strip())
    return titles


# 主题关键词映射：用于主题级去重
TOPIC_ENTITIES = [
    "mcp", "agent security", "agent safety", "agent governance",
    "claude code", "codex", "cursor", "kiro",
    "langgraph", "crewai", "openai agents sdk",
    "hermes agent", "context engineering", "memory poisoning",
]


def _extract_topics(text: str) -> set[str]:
    """从标题/摘要中提取主题实体"""
    text_lower = text.lower()
    return {t for t in TOPIC_ENTITIES if t in text_lower}


def _load_history_topics(days: int = 3) -> set[str]:
    """从历史简报中提取已覆盖的主题"""
    topics = set()
    briefings_dir = Path("output/briefings")
    if not briefings_dir.exists():
        return topics
    for i in range(1, days + 1):
        date_str = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        filepath = briefings_dir / f"{date_str}.md"
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            topics.update(_extract_topics(content))
    return topics


def deduplicate(state: CollectorState) -> CollectorState:
    seen_urls = set()
    seen_titles = []
    deduped = []
    history_titles = _load_history_titles()
    history_topics = _load_history_topics()

    for item in state["raw_items"]:
        url_key = _url_hash(item.get("url", ""))
        if url_key in seen_urls:
            continue
        title = item.get("title", "")
        # 标题相似度去重
        is_dup = any(_title_similarity(title, t) > 0.6 for t in seen_titles + history_titles)
        if is_dup:
            continue
        # 主题级去重：如果该条目的所有主题都已在历史中覆盖过，降低优先级
        item_topics = _extract_topics(f"{title} {item.get('summary', '')}")
        if item_topics and item_topics.issubset(history_topics):
            item["_topic_repeat"] = True  # 标记为主题重复，评分时降权
        seen_urls.add(url_key)
        seen_titles.append(title)
        deduped.append(item)

    state["deduped_items"] = deduped
    state["stats"] = {
        "raw_count": len(state["raw_items"]),
        "dedup_removed": len(state["raw_items"]) - len(deduped),
    }
    return state


# ============================================
# 评分节点
# ============================================

def score_items(state: CollectorState) -> CollectorState:
    scored = []
    now = datetime.now(timezone.utc)

    for item in state["deduped_items"]:
        # 时效性
        try:
            pub = datetime.fromisoformat(item.get("published", "").replace("Z", "+00:00"))
            hours = (now - pub).total_seconds() / 3600
            s_time = 5 if hours <= 24 else 4 if hours <= 48 else 3 if hours <= 72 else 2 if hours <= 168 else 1
        except (ValueError, TypeError):
            s_time = 2

        # 一手性
        source = item.get("source", "")
        s_primary = 5 if source.startswith("rss:") or source == "arxiv" else 4 if source == "github" else 3

        # 相关性
        text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
        hits = sum(1 for kw in AI_KEYWORDS if kw in text)
        s_relevance = 5 if hits >= 4 else 4 if hits >= 2 else 3 if hits >= 1 else 2

        # 实用性
        if source == "github" and item.get("stars", 0) > 500:
            s_practical = 5
        elif source == "hackernews" and item.get("score", 0) > 100:
            s_practical = 4
        elif source.startswith("rss:"):
            s_practical = 4
        else:
            s_practical = 3

        total = s_time + s_primary + s_relevance + s_practical
        # 主题重复降权：已在历史简报中覆盖过的主题，总分 -3
        if item.get("_topic_repeat"):
            total = max(total - 3, 0)
        scored.append({**item, "score_timeliness": s_time, "score_primary": s_primary,
                       "score_relevance": s_relevance, "score_practical": s_practical, "score_total": total})

    scored.sort(key=lambda x: x["score_total"], reverse=True)
    filtered = [s for s in scored if s["score_total"] >= 12]

    state["scored_items"] = filtered
    state["stats"]["score_filtered"] = len(scored) - len(filtered)
    state["stats"]["final_count"] = len(filtered)
    state["stats"]["filter_rate"] = round((1 - len(filtered) / max(len(state["raw_items"]), 1)) * 100)
    return state


# ============================================
# 简报生成
# ============================================

def _source_label(source: str) -> str:
    labels = {"hackernews": "Hacker News", "github": "GitHub", "arxiv": "arXiv"}
    return labels.get(source, source.replace("rss:", ""))


def generate_brief(state: CollectorState) -> CollectorState:
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    items = state["scored_items"]
    stats = state["stats"]

    github_items = [i for i in items if i.get("source") == "github"]
    arxiv_items = [i for i in items if i.get("source") == "arxiv"]
    hn_items = [i for i in items if i.get("source") == "hackernews"]
    rss_items = [i for i in items if i.get("source", "").startswith("rss:")]

    lines = [
        f"# AI Agent 每日简报 — {today}", "",
        "> Author: Walter Wang",
        f"> 采集时间: {now_time}",
        "> 来源: Hacker News API / GitHub API / arXiv API / RSS Feeds",
        "> 生成方式: LangGraph 自动化采集 Agent", "",
        "## 🔥 今日要闻", "",
    ]

    for item in items[:3]:
        lines.extend([
            f"### {item['title'][:80]}", "",
            f"- **来源**：[{_source_label(item.get('source', ''))}]({item.get('url', '')})",
            f"- **评分**：时效 {item.get('score_timeliness', 0)} / 一手 {item.get('score_primary', 0)} / 相关 {item.get('score_relevance', 0)} / 实用 {item.get('score_practical', 0)} = **{item.get('score_total', 0)}**",
            f"- **摘要**：{item.get('summary', '暂无摘要')[:200]}", "",
        ])

    if github_items:
        lines.extend(["## 📦 开源项目 & 工具", "",
                       "| 项目 | Stars | 语言 | 描述 | 链接 |",
                       "|------|-------|------|------|------|"])
        for item in github_items[:5]:
            name = item.get("title", "").split(":")[0].strip()
            lines.append(f"| {name} | {item.get('stars', 0):,} | {item.get('language', '-')} | {item.get('summary', '')[:60]} | [GitHub]({item.get('url', '')}) |")
        lines.append("")

    if arxiv_items:
        lines.extend(["## 📄 值得关注的论文", ""])
        for item in arxiv_items[:3]:
            lines.extend([
                f"### {item['title'][:80]}", "",
                f"- **作者**：{item.get('authors', '未知')}",
                f"- **摘要**：{item.get('summary', '')[:200]}",
                f"- **链接**：[arXiv]({item.get('url', '')})", "",
            ])

    if hn_items:
        lines.extend(["## 💬 社区讨论", ""])
        for item in hn_items[:5]:
            lines.append(f"- [{item['title']}]({item.get('url', '')})（{item.get('score', 0)} points）")
        lines.append("")

    lines.extend([
        "## 📊 本期统计", "",
        f"- 原始采集：{stats.get('raw_count', 0)} 条",
        f"- 去重排除：{stats.get('dedup_removed', 0)} 条",
        f"- 评分过滤：{stats.get('score_filtered', 0)} 条",
        f"- 最终收录：{stats.get('final_count', 0)} 条（总过滤率 {stats.get('filter_rate', 0)}%）",
        f"- 来源分布：HN {len(hn_items)} / GitHub {len(github_items)} / arXiv {len(arxiv_items)} / RSS {len(rss_items)}",
        "",
    ])

    state["daily_brief"] = "\n".join(lines)
    return state


# ============================================
# 输出节点
# ============================================

def save_brief(state: CollectorState) -> CollectorState:
    today = datetime.now().strftime("%Y-%m-%d")
    output_dir = Path("output/briefings")
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{today}.md"

    if filepath.exists() and state["scored_items"]:
        # 追加模式
        now_time = datetime.now().strftime("%H:%M")
        existing = filepath.read_text(encoding="utf-8")
        supplement = f"\n\n## 🔄 补充采集（{now_time}）\n\n"
        for item in state["scored_items"][:3]:
            supplement += f"### {item['title'][:80]}\n"
            supplement += f"- **来源**：[{_source_label(item.get('source', ''))}]({item.get('url', '')})\n"
            supplement += f"- **评分**：{item.get('score_total', 0)}\n"
            supplement += f"- **摘要**：{item.get('summary', '')[:200]}\n\n"
        filepath.write_text(existing + supplement, encoding="utf-8")
        print(f"📝 追加 {len(state['scored_items'])} 条到 {filepath}")
    elif not filepath.exists():
        filepath.write_text(state["daily_brief"], encoding="utf-8")
        print(f"📝 简报已保存到 {filepath}")
    else:
        print("✅ 今日已采集完毕，暂无新增内容")

    # Bark 推送通知
    try:
        from brand_agent.config import settings
        if settings.bark_url:
            from brand_agent.notify import push_bark, format_briefing_for_bark
            title, body = format_briefing_for_bark(state["scored_items"], state["stats"])
            push_bark(settings.bark_url, title, body)
    except Exception as e:
        print(f"⚠️ 推送跳过：{e}")

    # 保存原始数据
    data_dir = Path("output/data")
    data_dir.mkdir(parents=True, exist_ok=True)
    data_dir.joinpath(f"{today}.json").write_text(
        json.dumps(state["scored_items"], ensure_ascii=False, indent=2), encoding="utf-8")

    return state


# ============================================
# 构建工作流
# ============================================

def build_collector_graph():
    graph = StateGraph(CollectorState)
    graph.add_node("fetch_hn", fetch_hackernews)
    graph.add_node("fetch_github", fetch_github_trending)
    graph.add_node("fetch_arxiv", fetch_arxiv)
    graph.add_node("fetch_rss", fetch_rss_feeds)
    graph.add_node("dedup", deduplicate)
    graph.add_node("score", score_items)
    graph.add_node("brief", generate_brief)
    graph.add_node("save", save_brief)

    graph.set_entry_point("fetch_hn")
    graph.add_edge("fetch_hn", "fetch_github")
    graph.add_edge("fetch_github", "fetch_arxiv")
    graph.add_edge("fetch_arxiv", "fetch_rss")
    graph.add_edge("fetch_rss", "dedup")
    graph.add_edge("dedup", "score")
    graph.add_edge("score", "brief")
    graph.add_edge("brief", "save")
    graph.add_edge("save", END)

    return graph.compile()


def collect_trending() -> dict:
    """CLI 入口：运行完整采集流程"""
    workflow = build_collector_graph()
    result = workflow.invoke({
        "raw_items": [], "deduped_items": [], "scored_items": [],
        "daily_brief": "", "stats": {},
    })
    return {"items": result["scored_items"], "brief": result["daily_brief"], "stats": result["stats"]}


if __name__ == "__main__":
    print("🚀 开始采集 AI Agent 每日热点...\n")
    result = collect_trending()
    print(f"\n📊 采集完成：{result['stats']}")
