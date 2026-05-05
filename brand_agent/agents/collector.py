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
    topic: str                  # 主题标识：ai-agent / china-tech / global-tech
    raw_items: list[dict]
    deduped_items: list[dict]
    scored_items: list[dict]
    daily_brief: str
    stats: dict


# ============================================
# 主题配置（对齐 briefing-tools.py）
# ============================================

# 每个主题包含：RSS 源、HN 搜索词、GitHub 查询、关键词、是否启用 arXiv
TOPIC_CONFIG = {
    "ai-agent": {
        "display_name": "AI Agent",
        "hn_terms": ["AI agent", "LLM", "MCP protocol", "Claude", "coding agent", "LangGraph"],
        "github_queries": [
            "ai agent pushed:>{since} stars:>100",
            "mcp server pushed:>{since} stars:>50",
            "llm framework pushed:>{since} stars:>100",
            "coding agent pushed:>{since} stars:>50",
        ],
        "keywords": [
            "ai agent", "llm agent", "ai coding", "mcp", "a2a protocol",
            "langgraph", "crewai", "openai", "anthropic", "claude",
            "rag", "vector", "embedding", "function calling", "tool use",
            "multi-agent", "context engineering", "prompt engineering",
            "coding agent", "cursor", "copilot", "kiro",
            "ai safety", "ai governance", "agent security",
            "langchain", "autogen", "semantic kernel",
        ],
        "enable_arxiv": True,
        "rss_feeds": [
            {"name": "LangChain Blog", "url": "https://blog.langchain.com/rss.xml"},
            {"name": "Anthropic Research", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_research.xml", "timeout": 30},
            {"name": "Anthropic News", "url": "https://raw.githubusercontent.com/Olshansk/rss-feeds/main/feeds/feed_anthropic_news.xml", "timeout": 30},
            {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml"},
            {"name": "Google AI Blog", "url": "https://blog.google/technology/ai/rss/"},
            {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml"},
            {"name": "Wired AI", "url": "https://www.wired.com/feed/tag/ai/latest/rss"},
            {"name": "Hacker News AI", "url": "https://hnrss.org/newest?q=AI+agent+OR+MCP+OR+LLM&points=30"},
            {"name": "Hacker News AI 关键词", "url": "https://hnrss.org/newest?q=LangGraph+OR+CrewAI+OR+Claude+OR+RAG+OR+function+calling+OR+context+engineering&points=20"},
        ],
    },
    "china-tech": {
        "display_name": "国内科技",
        "hn_terms": ["DeepSeek", "Qwen", "China AI", "Baidu AI", "Alibaba AI"],
        "github_queries": [
            "DeepSeek pushed:>{since} stars:>50",
            "Qwen pushed:>{since} stars:>50",
        ],
        "keywords": [
            "deepseek", "qwen", "baidu", "alibaba", "tencent",
            "moonshot", "zhipu", "minimax", "glm", "kimi",
            "字节", "阿里", "腾讯", "百度", "华为", "小米",
            "国产大模型", "中国 ai", "开源模型",
        ],
        "enable_arxiv": False,
        "rss_feeds": [
            {"name": "36氪", "url": "https://36kr.com/feed"},
            {"name": "InfoQ CN", "url": "https://www.infoq.cn/feed"},
            {"name": "极客公园", "url": "https://www.geekpark.net/rss"},
            {"name": "量子位", "url": "https://www.qbitai.com/feed"},
            {"name": "开源中国", "url": "https://www.oschina.net/news/rss"},
            {"name": "少数派", "url": "https://sspai.com/feed"},
            {"name": "Hacker News 中国科技", "url": "https://hnrss.org/newest?q=DeepSeek+OR+Qwen+OR+Baidu+AI+OR+China+AI&points=10"},
        ],
    },
    "global-tech": {
        "display_name": "国际科技",
        "hn_terms": ["Rust", "TypeScript", "Kubernetes", "AWS", "security"],
        "github_queries": [
            "rust pushed:>{since} stars:>500",
            "typescript pushed:>{since} stars:>500",
            "kubernetes pushed:>{since} stars:>200",
        ],
        "keywords": [
            "rust", "typescript", "javascript", "golang", "python",
            "kubernetes", "docker", "aws", "gcp", "azure", "cloudflare",
            "security", "vulnerability", "cve", "zero-day",
            "open source", "devops", "sre", "observability",
        ],
        "enable_arxiv": False,
        "rss_feeds": [
            {"name": "Hacker News Top", "url": "https://hnrss.org/frontpage?count=30"},
            {"name": "TechCrunch", "url": "https://techcrunch.com/feed/"},
            {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
            {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
            {"name": "GitHub Blog", "url": "https://github.blog/feed/"},
            {"name": "Product Hunt", "url": "https://www.producthunt.com/feed"},
            {"name": "AWS Blog", "url": "https://aws.amazon.com/blogs/aws/feed/"},
            {"name": "Cloudflare Blog", "url": "https://blog.cloudflare.com/rss/"},
            {"name": "Kubernetes Blog", "url": "https://kubernetes.io/feed.xml"},
            {"name": "Hacker News 开发者", "url": "https://hnrss.org/newest?q=Rust+OR+TypeScript+OR+Kubernetes+OR+AWS+OR+security+vulnerability&points=20"},
        ],
    },
}


def get_topic_config(topic: str) -> dict:
    """获取主题配置，未知主题回退到 ai-agent"""
    return TOPIC_CONFIG.get(topic, TOPIC_CONFIG["ai-agent"])


# ============================================
# 采集节点
# ============================================

def fetch_hackernews(state: CollectorState) -> CollectorState:
    """从 Hacker News Algolia API 采集主题相关热帖"""
    items = []
    config = get_topic_config(state.get("topic", "ai-agent"))
    search_terms = config["hn_terms"]
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
    """从 GitHub API 搜索近期热门项目（按主题筛选）"""
    items = []
    since = (datetime.now(timezone.utc) - timedelta(days=7)).strftime("%Y-%m-%d")
    config = get_topic_config(state.get("topic", "ai-agent"))
    queries = [q.format(since=since) for q in config["github_queries"]]

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
    """从 arXiv API 采集最新 AI Agent 论文（仅 ai-agent 主题启用）"""
    config = get_topic_config(state.get("topic", "ai-agent"))
    if not config.get("enable_arxiv"):
        return state

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
    """从主题配置的 RSS 源采集最新文章（并发）"""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    config = get_topic_config(state.get("topic", "ai-agent"))
    rss_feeds = config["rss_feeds"]
    items = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    def _fetch_one(feed_cfg: dict) -> tuple[str, list[dict]]:
        source_name = feed_cfg["name"]
        feed_url = feed_cfg["url"]
        timeout = feed_cfg.get("timeout", 10)
        fetched = []
        try:
            resp = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:8]:
                published = entry.get("published_parsed") or entry.get("updated_parsed")
                if published:
                    pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                    if pub_dt < cutoff:
                        continue
                    pub_str = pub_dt.isoformat()
                else:
                    pub_str = ""
                fetched.append({
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
        return source_name, fetched

    # 并发采集（对齐 briefing-tools.py 的并发策略）
    max_workers = min(len(rss_feeds), 8) if rss_feeds else 1
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_fetch_one, cfg): cfg for cfg in rss_feeds}
        for future in as_completed(futures):
            _, fetched = future.result()
            items.extend(fetched)

    state["raw_items"].extend(items[:20])
    return state


def fetch_web_search(state: CollectorState) -> CollectorState:
    """Web Search 补充采集节点

    策略：
    - 有 Tavily API key → 用 Tavily（质量高）
    - 否则 → 用 DuckDuckGo HTML 搜索（免费，失败不阻塞）
    - 查询词来自主题的 hn_terms（与 HN 搜索保持一致）

    静默失败：网络错误、解析失败、无 API key 都不抛异常。
    """
    topic = state.get("topic", "ai-agent")
    config = get_topic_config(topic)
    queries = config["hn_terms"][:3]  # 只用前 3 个词，控制请求量

    items = []

    # 优先 Tavily
    try:
        from brand_agent.config import settings
        tavily_key = getattr(settings, "tavily_api_key", "")
    except Exception:
        tavily_key = ""

    if tavily_key:
        items.extend(_tavily_search(queries, tavily_key))
    else:
        items.extend(_duckduckgo_search(queries))

    if items:
        print(f"[Web Search] 采集 {len(items)} 条补充内容")
    state["raw_items"].extend(items[:10])
    return state


def _tavily_search(queries: list[str], api_key: str) -> list[dict]:
    """Tavily 搜索（付费 API，质量高）"""
    items = []
    for query in queries:
        try:
            resp = httpx.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "max_results": 3,
                    "days": 2,
                    "topic": "news",
                },
                timeout=15,
            )
            if resp.status_code != 200:
                continue
            for r in resp.json().get("results", []):
                items.append({
                    "source": "web:tavily",
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "score": 0,
                    "published": r.get("published_date", ""),
                    "summary": r.get("content", "")[:300],
                    "tags": [],
                })
        except Exception as e:
            print(f"[Tavily] 搜索 '{query}' 失败: {e}")
    return items


def _duckduckgo_search(queries: list[str]) -> list[dict]:
    """DuckDuckGo 搜索（免费，通过 HTML 端点）

    失败时返回空列表，不阻塞主流程。
    """
    items = []
    for query in queries:
        try:
            resp = httpx.get(
                "https://html.duckduckgo.com/html/",
                params={"q": f"{query} site:news OR 2026"},
                headers={"User-Agent": "Mozilla/5.0 (compatible; BrandAgent/1.0)"},
                timeout=10,
                follow_redirects=True,
            )
            if resp.status_code != 200:
                continue
            # 从 HTML 中提取结果（DuckDuckGo 的 HTML 结构相对稳定）
            pattern = re.compile(
                r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>.*?'
                r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
                re.DOTALL,
            )
            matches = pattern.findall(resp.text)[:3]
            for url, title, snippet in matches:
                # 清理 HTML 标签
                clean_title = re.sub(r'<[^>]+>', '', title).strip()
                clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                if clean_title and url.startswith("http"):
                    items.append({
                        "source": "web:duckduckgo",
                        "title": clean_title,
                        "url": url,
                        "score": 0,
                        "published": "",
                        "summary": clean_snippet[:300],
                        "tags": [],
                    })
        except Exception as e:
            print(f"[DuckDuckGo] 搜索 '{query}' 失败: {e}")
    return items


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


def _load_history_titles(days: int = 3, topic: str = "ai-agent") -> list[str]:
    """从新路径格式加载历史简报标题用于去重"""
    titles = []
    for i in range(1, days + 1):
        dt = datetime.now() - timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        # 新路径格式
        filepath = Path("output/briefings") / topic / year / month / f"{date_str}.md"
        if not filepath.exists():
            # 兼容旧路径格式
            filepath = Path("output/briefings") / f"{date_str}.md"
        if filepath.exists():
            for line in filepath.read_text(encoding="utf-8").split("\n"):
                if line.startswith("### "):
                    # 去掉序号前缀如 "### 1. "
                    title = line[4:].strip()
                    if title and title[0].isdigit() and ". " in title:
                        title = title.split(". ", 1)[1]
                    titles.append(title)
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


def _load_history_topics(days: int = 3, topic: str = "ai-agent") -> set[str]:
    """从历史简报中提取已覆盖的主题"""
    topics = set()
    for i in range(1, days + 1):
        dt = datetime.now() - timedelta(days=i)
        date_str = dt.strftime("%Y-%m-%d")
        year = dt.strftime("%Y")
        month = dt.strftime("%m")
        # 新路径格式
        filepath = Path("output/briefings") / topic / year / month / f"{date_str}.md"
        if not filepath.exists():
            # 兼容旧路径格式
            filepath = Path("output/briefings") / f"{date_str}.md"
        if filepath.exists():
            content = filepath.read_text(encoding="utf-8")
            topics.update(_extract_topics(content))
    return topics


def _load_cross_topic_titles(current_topic: str) -> list[str]:
    """加载当天其他主题简报中已收录的标题，用于跨简报去重

    对齐 briefing-tools.py：三个主题间互相过滤重复内容，避免同一事件在
    多个简报中重复出现。
    """
    titles = []
    today = datetime.now().strftime("%Y-%m-%d")
    year = datetime.now().strftime("%Y")
    month = datetime.now().strftime("%m")
    other_topics = [t for t in TOPIC_CONFIG.keys() if t != current_topic]

    for ot in other_topics:
        filepath = Path("output/briefings") / ot / year / month / f"{today}.md"
        if filepath.exists():
            for line in filepath.read_text(encoding="utf-8").split("\n"):
                if line.startswith("### "):
                    title = line[4:].strip()
                    # 去掉序号前缀如 "### 1. "
                    if title and title[0].isdigit() and ". " in title:
                        title = title.split(". ", 1)[1]
                    titles.append(title)
    return titles


def deduplicate(state: CollectorState) -> CollectorState:
    seen_urls = set()
    seen_titles = []
    deduped = []
    topic = state.get("topic", "ai-agent")
    history_titles = _load_history_titles(topic=topic)
    history_topics = _load_history_topics(topic=topic)
    # 跨简报去重：加载当天其他主题已收录的标题
    cross_topic_titles = _load_cross_topic_titles(current_topic=topic)

    cross_topic_removed = 0
    for item in state["raw_items"]:
        url_key = _url_hash(item.get("url", ""))
        if url_key in seen_urls:
            continue
        title = item.get("title", "")
        # 标题相似度去重（当前批次 + 历史）
        is_dup = any(_title_similarity(title, t) > 0.6 for t in seen_titles + history_titles)
        if is_dup:
            continue
        # 跨简报去重：阈值略宽松（0.5），只要内容主体相似就排除
        is_cross_dup = any(_title_similarity(title, t) > 0.5 for t in cross_topic_titles)
        if is_cross_dup:
            cross_topic_removed += 1
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
        "cross_topic_removed": cross_topic_removed,
    }
    return state


# ============================================
# 评分节点
# ============================================

def _llm_score_relevance(items: list[dict], topic: str, top_n: int = 30) -> dict[str, int]:
    """用 LLM 批量评估相关性（1-5 分），返回 {url: score} 映射

    只对前 top_n 条做 LLM 评分以控制成本。无 API key 或调用失败时返回空字典。
    调用方应 fallback 到规则评分。
    """
    from brand_agent.llm_factory import create_llm, get_backend_name

    if not items:
        return {}

    llm = create_llm(temperature=0, timeout=30, max_tokens=2000)
    if llm is None:
        return {}

    candidates = items[:top_n]
    topic_desc = {
        "ai-agent": "AI Agent / LLM / Coding Agent / MCP 协议等 AI 工程领域",
        "china-tech": "国内科技动态、国产大模型、中国互联网公司新闻",
        "global-tech": "全球科技趋势、开发者工具、云平台、安全漏洞",
    }.get(topic, "AI 技术")

    # 构造评分提示：URL -> title + summary，避免编号歧义
    lines = []
    for i, item in enumerate(candidates, 1):
        title = item.get("title", "")[:120]
        summary = item.get("summary", "")[:200]
        lines.append(f"{i}. [{title}] — {summary}")

    prompt = f"""你是一名资深技术编辑，正在为「{topic_desc}」方向的开发者简报做相关性评分。

请对以下 {len(candidates)} 条内容按相关性和价值打分（1-5 分整数）：
- 5: 高度相关且有实操价值（新工具/框架发布、深度技术文章、重要论文）
- 4: 相关性强（行业动态、可供参考的最佳实践）
- 3: 一般相关（泛讨论、新闻摘要）
- 2: 弱相关（擦边话题）
- 1: 不相关或营销/SEO 内容

条目列表:
{chr(10).join(lines)}

只输出 JSON 数组（不要任何解释性文字）：[{{"idx": 1, "score": 5}}, {{"idx": 2, "score": 3}}, ...]"""

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)

        # 提取 JSON 数组
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if not match:
            print("[LLM 评分] 响应中未找到 JSON 数组，fallback 到规则评分")
            return {}
        scores = json.loads(match.group(0))

        # 映射回 URL
        result = {}
        for entry in scores:
            idx = entry.get("idx", 0) - 1
            score = entry.get("score", 3)
            if 0 <= idx < len(candidates):
                url = candidates[idx].get("url", "")
                if url:
                    result[url] = max(1, min(5, int(score)))
        print(f"[LLM 评分/{get_backend_name()}] 成功评分 {len(result)} 条")
        return result
    except Exception as e:
        print(f"[LLM 评分] 调用失败，fallback 到规则评分: {e}")
        return {}


def score_items(state: CollectorState) -> CollectorState:
    scored = []
    now = datetime.now(timezone.utc)
    topic = state.get("topic", "ai-agent")
    config = get_topic_config(topic)
    topic_keywords = config["keywords"]

    # 先按规则做粗筛，再对头部送 LLM 做相关性复核
    # 粗筛阶段用一个简单的"按 HN 分数/GitHub stars/发布时间"排序，保留前 30 条候选
    def _quick_rank(item: dict) -> float:
        source = item.get("source", "")
        score = item.get("score", 0)
        stars = item.get("stars", 0)
        # 综合信号：stars * 0.5 + HN points + RSS 基础分
        return stars * 0.5 + score + (10 if source.startswith("rss:") else 0)

    candidates = sorted(state["deduped_items"], key=_quick_rank, reverse=True)
    # LLM 评分（只对头部做，成本可控；返回 {url: llm_score}）
    llm_scores = _llm_score_relevance(candidates, topic=topic, top_n=30)

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

        # 相关性（LLM 优先，fallback 规则）
        url = item.get("url", "")
        if url and url in llm_scores:
            s_relevance = llm_scores[url]
            item["_score_source"] = "llm"
        else:
            text = f"{item.get('title', '')} {item.get('summary', '')}".lower()
            hits = sum(1 for kw in topic_keywords if kw in text)
            s_relevance = 5 if hits >= 4 else 4 if hits >= 2 else 3 if hits >= 1 else 2
            item["_score_source"] = "rule"

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
    state["stats"]["llm_scored"] = len(llm_scores)
    state["stats"]["filter_rate"] = round((1 - len(filtered) / max(len(state["raw_items"]), 1)) * 100)
    return state


# ============================================
# 简报生成
# ============================================

def _source_label(source: str) -> str:
    labels = {"hackernews": "Hacker News", "github": "GitHub", "arxiv": "arXiv"}
    return labels.get(source, source.replace("rss:", ""))


def _format_tags(item: dict) -> str:
    """从 item 的 tags 列表生成 Markdown 标签字符串"""
    tags = item.get("tags", [])
    if not tags:
        # 从来源和关键词推断标签
        source = item.get("source", "")
        inferred = []
        if source == "github":
            inferred.append("开源")
        elif source == "arxiv":
            inferred.append("论文")
        elif source == "hackernews":
            inferred.append("社区")
        elif source.startswith("rss:"):
            inferred.append(source.replace("rss:", ""))
        tags = inferred
    return " ".join(f"`{t}`" for t in tags[:5]) if tags else "`AI`"


def generate_brief(state: CollectorState) -> CollectorState:
    """生成简报 Markdown，对齐 Kiro Hooks 新格式（头条 + 项目 + 论文 + 行业 + 社区 + 趋势 + 统计）"""
    today = datetime.now().strftime("%Y-%m-%d")
    now_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    items = state["scored_items"]
    stats = state["stats"]

    github_items = [i for i in items if i.get("source") == "github"]
    arxiv_items = [i for i in items if i.get("source") == "arxiv"]
    hn_items = [i for i in items if i.get("source") == "hackernews"]
    rss_items = [i for i in items if i.get("source", "").startswith("rss:")]

    # 头条：取评分最高的前 3 条（不限来源）
    top_items = items[:3]

    lines = [
        f"# AI Agent 简报 — {today}", "",
        "> Author: Walter Wang",
        f"> 采集时间: {now_time}",
        "> 来源: Hacker News / GitHub / arXiv / RSS Feeds",
        "> 生成方式: Brand Agent 自动化采集", "",
    ]

    # 🔥 今日要闻
    if top_items:
        lines.extend([f"## 🔥 今日要闻（{len(top_items)} 条）", ""])
        for i, item in enumerate(top_items, 1):
            lines.extend([
                f"### {i}. {item['title'][:80]}", "",
                f"- **来源**：[{_source_label(item.get('source', ''))}]({item.get('url', '')})",
                f"- **标签**：{_format_tags(item)}",
                f"- **评分**：时效 {item.get('score_timeliness', 0)} / 一手 {item.get('score_primary', 0)} / 相关 {item.get('score_relevance', 0)} / 实用 {item.get('score_practical', 0)} = 总分 {item.get('score_total', 0)}",
                f"- **摘要**：{item.get('summary', '暂无摘要')[:300]}", "",
            ])

    # 📦 开源项目 & 工具
    if github_items:
        lines.extend(["## 📦 开源项目 & 工具", "",
                       "| 项目 | Stars | 语言 | 描述 | 链接 |",
                       "|------|-------|------|------|------|"])
        for item in github_items[:5]:
            name = item.get("title", "").split(":")[0].strip()
            desc = item.get("summary", "")[:60]
            lines.append(f"| {name} | {item.get('stars', 0):,} | {item.get('language', '-')} | {desc} | [GitHub]({item.get('url', '')}) |")
        lines.append("")

    # 📄 值得关注的论文
    if arxiv_items:
        lines.extend(["## 📄 值得关注的论文", ""])
        for item in arxiv_items[:3]:
            lines.extend([
                f"### {item['title'][:80]}", "",
                f"- **作者**：{item.get('authors', '未知')}",
                f"- **摘要**：{item.get('summary', '')[:300]}",
                f"- **链接**：[arXiv]({item.get('url', '')})", "",
            ])

    # 🏢 行业动态（RSS 来源）
    if rss_items:
        lines.extend(["## 🏢 行业动态", ""])
        for item in rss_items[:5]:
            lines.extend([
                f"### {item['title'][:80]}", "",
                f"- **来源**：[{_source_label(item.get('source', ''))}]({item.get('url', '')})",
                f"- **摘要**：{item.get('summary', '')[:200]}", "",
            ])

    # 💬 社区讨论
    if hn_items:
        lines.extend(["## 💬 社区讨论", ""])
        for item in hn_items[:5]:
            lines.append(f"- [{item['title']}]({item.get('url', '')})（{item.get('score', 0)} points）")
        lines.append("")

    # 📈 趋势追踪（主题重复项标记为趋势）
    trend_items = [i for i in state.get("deduped_items", []) if i.get("_topic_repeat")]
    if trend_items:
        lines.extend(["## 📈 趋势追踪", ""])
        for item in trend_items[:5]:
            topics = _extract_topics(f"{item.get('title', '')} {item.get('summary', '')}")
            topic_str = "、".join(topics) if topics else "持续关注"
            lines.append(f"- 🔺 **{topic_str}**：{item.get('title', '')[:60]}")
        lines.append("")

    # 📊 本期统计
    lines.extend([
        "## 📊 本期统计", "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 原始采集 | {stats.get('raw_count', 0)} 条 |",
        f"| 去重排除 | {stats.get('dedup_removed', 0)} 条 |",
        f"| 评分过滤 | {stats.get('score_filtered', 0)} 条 |",
        f"| 最终收录 | {stats.get('final_count', 0)} 条 |",
        f"| 来源分布 | HN {len(hn_items)} / GitHub {len(github_items)} / arXiv {len(arxiv_items)} / RSS {len(rss_items)} |",
        "",
    ])

    state["daily_brief"] = "\n".join(lines)
    return state


# ============================================
# 输出节点
# ============================================

def save_brief(state: CollectorState) -> CollectorState:
    """保存简报到新路径格式：output/briefings/{topic}/YYYY/MM/YYYY-MM-DD.md"""
    today = datetime.now().strftime("%Y-%m-%d")
    year = datetime.now().strftime("%Y")
    month = datetime.now().strftime("%m")
    topic = state.get("topic", "ai-agent")

    output_dir = Path("output/briefings") / topic / year / month
    output_dir.mkdir(parents=True, exist_ok=True)
    filepath = output_dir / f"{today}.md"

    if filepath.exists() and state["scored_items"]:
        # 追加模式
        existing = filepath.read_text(encoding="utf-8")
        supplement = "\n\n## 🔄 补充采集\n\n"
        for item in state["scored_items"][:3]:
            supplement += f"### {item['title'][:80]}\n"
            supplement += f"- **来源**：[{_source_label(item.get('source', ''))}]({item.get('url', '')})\n"
            supplement += f"- **评分**：时效 {item.get('score_timeliness', 0)} / 一手 {item.get('score_primary', 0)} / 相关 {item.get('score_relevance', 0)} / 实用 {item.get('score_practical', 0)} = 总分 {item.get('score_total', 0)}\n"
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
    graph.add_node("fetch_web", fetch_web_search)
    graph.add_node("dedup", deduplicate)
    graph.add_node("score", score_items)
    graph.add_node("brief", generate_brief)
    graph.add_node("save", save_brief)

    graph.set_entry_point("fetch_hn")
    graph.add_edge("fetch_hn", "fetch_github")
    graph.add_edge("fetch_github", "fetch_arxiv")
    graph.add_edge("fetch_arxiv", "fetch_rss")
    graph.add_edge("fetch_rss", "fetch_web")
    graph.add_edge("fetch_web", "dedup")
    graph.add_edge("dedup", "score")
    graph.add_edge("score", "brief")
    graph.add_edge("brief", "save")
    graph.add_edge("save", END)

    return graph.compile()


def collect_trending(topic: str = "ai-agent") -> dict:
    """CLI 入口：运行完整采集流程

    Args:
        topic: 主题标识，支持 ai-agent / china-tech / global-tech
    """
    workflow = build_collector_graph()
    result = workflow.invoke({
        "topic": topic,
        "raw_items": [], "deduped_items": [], "scored_items": [],
        "daily_brief": "", "stats": {},
    })
    return {"items": result["scored_items"], "brief": result["daily_brief"], "stats": result["stats"]}


if __name__ == "__main__":
    print("🚀 开始采集 AI Agent 每日热点...\n")
    result = collect_trending()
    print(f"\n📊 采集完成：{result['stats']}")
