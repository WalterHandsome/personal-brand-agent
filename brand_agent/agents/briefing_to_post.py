"""简报 → 社交内容 生成器

从当日最新简报中提取头条，生成可分发的社交内容：
- X/Twitter Thread（5-6 条，每条 ≤ 280 字符）
- 博客摘要（Markdown）

有 LLM API key 时用 LLM 改写，否则用规则提取。生成的内容保存为标准
article 对象到 data/articles/，后续可通过 distribute 命令分发。
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import TypedDict

from langgraph.graph import StateGraph, END


class BriefToPostState(TypedDict):
    """简报 → 内容生成 Agent 的状态"""
    topic: str                   # 主题标识
    briefing_path: str           # 简报 Markdown 路径
    briefing_content: str        # 简报原文
    headlines: list[dict]        # 提取的头条（title/url/summary）
    twitter_thread: list[str]    # Twitter Thread
    blog_excerpt: str            # 博客摘要
    article: dict                # 最终 article 对象
    saved_path: str              # 保存路径


def _latest_briefing_path(topic: str) -> Path | None:
    """查找当天或最近一天的简报文件"""
    from brand_agent.agents.collector import TOPIC_CONFIG

    if topic not in TOPIC_CONFIG:
        return None

    # 优先找今天
    now = datetime.now()
    today_path = (
        Path("output/briefings") / topic
        / now.strftime("%Y") / now.strftime("%m")
        / f"{now.strftime('%Y-%m-%d')}.md"
    )
    if today_path.exists():
        return today_path

    # fallback：找 output/briefings/{topic}/ 下最新的 .md
    topic_dir = Path("output/briefings") / topic
    if topic_dir.exists():
        md_files = sorted(topic_dir.rglob("*.md"), reverse=True)
        if md_files:
            return md_files[0]
    return None


def load_briefing(state: BriefToPostState) -> BriefToPostState:
    """加载简报文件"""
    topic = state.get("topic", "ai-agent")
    path = _latest_briefing_path(topic)
    if not path:
        state["briefing_content"] = ""
        state["briefing_path"] = ""
        return state

    state["briefing_path"] = str(path)
    state["briefing_content"] = path.read_text(encoding="utf-8")
    return state


def extract_headlines(state: BriefToPostState) -> BriefToPostState:
    """从简报中解析出今日要闻（带序号的 ### 开头条目）

    规则解析，不依赖 LLM。简报新格式为：
        ## 🔥 今日要闻（N 条）

        ### 1. 标题
        - **来源**：[xxx](url)
        - **标签**：...
        - **评分**：...
        - **摘要**：xxx
    """
    content = state.get("briefing_content", "")
    if not content:
        state["headlines"] = []
        return state

    # 截取「今日要闻」板块
    news_match = re.search(
        r"##\s*🔥\s*今日要闻.*?(?=^##\s)", content, re.MULTILINE | re.DOTALL
    )
    news_block = news_match.group(0) if news_match else content

    # 提取每条头条：### 1. xxx ... 直到下一个 ### 或 ##
    headline_pattern = re.compile(
        r"###\s+\d+\.\s*(.+?)\n\n(.*?)(?=\n###\s|\n##\s|\Z)",
        re.DOTALL,
    )
    headlines = []
    for match in headline_pattern.finditer(news_block):
        title = match.group(1).strip()
        body = match.group(2)

        # 提取来源 URL
        url_match = re.search(r"来源.*?\((https?://[^)]+)\)", body)
        url = url_match.group(1) if url_match else ""

        # 提取摘要
        summary_match = re.search(r"\*\*摘要\*\*：(.+?)(?=\n-|\n\n|\Z)", body, re.DOTALL)
        summary = summary_match.group(1).strip() if summary_match else ""

        headlines.append({"title": title, "url": url, "summary": summary})

    state["headlines"] = headlines[:3]  # 只取前 3 条做内容生成
    return state


def _rule_based_thread(topic: str, headlines: list[dict]) -> list[str]:
    """规则兜底：从头条生成一条简单的 Twitter Thread

    格式：
    - 第 1 条：🧵 日期 + 主题开场
    - 第 2~4 条：每条要闻一条推文
    - 最后一条：行动召唤 CTA
    """
    today = datetime.now().strftime("%Y-%m-%d")
    topic_name = {
        "ai-agent": "AI Agent",
        "china-tech": "国内科技",
        "global-tech": "国际科技",
    }.get(topic, topic)

    tweets = [
        f"🧵 {topic_name} 简报 · {today}\n\n今日精选 {len(headlines)} 条值得关注的内容，一起看 👇"
    ]

    for i, item in enumerate(headlines, 1):
        title = item.get("title", "")[:120]
        summary = item.get("summary", "")[:150]
        url = item.get("url", "")
        tweet = f"{i}/ {title}"
        if summary:
            tweet += f"\n\n{summary}"
        if url:
            tweet += f"\n\n🔗 {url}"
        if len(tweet) > 275:
            tweet = tweet[:272] + "..."
        tweets.append(tweet)

    tweets.append(
        f"📬 完整简报（每日更新）：github.com/search?q={topic}+briefing\n\n"
        "💬 你关注哪条？欢迎讨论"
    )
    return tweets


def _llm_rewrite_thread(topic: str, headlines: list[dict]) -> list[str] | None:
    """用 LLM 改写为更有传播力的 Thread，失败返回 None"""
    from brand_agent.llm_factory import create_llm, get_backend_name

    if not headlines:
        return None

    llm = create_llm(temperature=0.7, timeout=60, max_tokens=3000)
    if llm is None:
        return None

    topic_name = {
        "ai-agent": "AI Agent / LLM 开发",
        "china-tech": "国内科技",
        "global-tech": "全球科技趋势",
    }.get(topic, topic)

    items_text = "\n\n".join(
        f"{i}. {h['title']}\n摘要: {h.get('summary', '')}\n链接: {h.get('url', '')}"
        for i, h in enumerate(headlines, 1)
    )

    # 使用特殊分隔符而非 JSON，规避引号转义问题
    separator = "===TWEET==="
    prompt = f"""你是技术博主 Walter Wang，擅长在 X/Twitter 上传播 {topic_name} 相关内容。

基于以下 {len(headlines)} 条今日要闻，生成一条高质量的 Twitter Thread（中文）：
1. 第一条：吸引人的开场，提炼今日最核心的主题（≤ 240 字符）
2. 接下来每条：一条要闻一个推文，给出你的解读而不是复述（≤ 260 字符，带链接）
3. 最后一条：行动召唤（CTA）或金句收尾

要求：
- 每条 ≤ 280 字符（含链接）
- 使用 emoji 但不滥用
- 技术术语用英文
- 语气真诚，像和朋友分享

今日要闻:
{items_text}

输出格式：每条推文用 `{separator}` 分隔，不要编号，不要解释。示例：
第一条推文内容
{separator}
第二条推文内容
{separator}
第三条推文内容"""

    try:
        response = llm.invoke(prompt)
        text = response.content if hasattr(response, "content") else str(response)

        # 按分隔符拆分
        parts = [p.strip() for p in text.split(separator) if p.strip()]
        # 去除可能的 markdown 代码块包裹
        cleaned = []
        for p in parts:
            p = re.sub(r"^```\w*\s*", "", p)
            p = re.sub(r"\s*```$", "", p)
            p = p.strip()
            if p:
                cleaned.append(p)

        if len(cleaned) < 2:
            print(f"[LLM 改写 Thread] 拆分结果异常（{len(cleaned)} 条），fallback 到规则模板")
            return None

        # 硬截断 280 字符
        tweets = [t[:278] + ".." if len(t) > 280 else t for t in cleaned]
        print(f"[LLM 改写 Thread/{get_backend_name()}] 生成 {len(tweets)} 条")
        return tweets
    except Exception as e:
        print(f"[LLM 改写 Thread] 失败，fallback 到规则模板: {e}")
        return None


def generate_twitter_thread(state: BriefToPostState) -> BriefToPostState:
    """生成 Twitter Thread：LLM 优先，规则兜底"""
    headlines = state.get("headlines", [])
    topic = state.get("topic", "ai-agent")

    thread = _llm_rewrite_thread(topic, headlines)
    if not thread:
        thread = _rule_based_thread(topic, headlines)

    state["twitter_thread"] = thread
    return state


def generate_blog_excerpt(state: BriefToPostState) -> BriefToPostState:
    """生成博客摘要（直接用简报头部的 Markdown，便于二次编辑）"""
    headlines = state.get("headlines", [])
    topic = state.get("topic", "ai-agent")
    today = datetime.now().strftime("%Y-%m-%d")

    lines = [f"## {topic} 简报摘要 — {today}", ""]
    for i, h in enumerate(headlines, 1):
        title = h.get("title", "")
        url = h.get("url", "")
        summary = h.get("summary", "")
        lines.append(f"### {i}. [{title}]({url})")
        lines.append("")
        if summary:
            lines.append(summary)
            lines.append("")

    state["blog_excerpt"] = "\n".join(lines)
    return state


def save_article(state: BriefToPostState) -> BriefToPostState:
    """保存为标准 article 对象，后续可通过 distribute 命令分发"""
    topic = state.get("topic", "ai-agent")
    today = datetime.now().strftime("%Y-%m-%d")
    article_id = f"briefing-{topic}-{today}"

    article = {
        "id": article_id,
        "title": f"{topic} 简报 · {today}",
        "date": today,
        "tags": [topic, "briefing", "daily"],
        "excerpt": state.get("blog_excerpt", "")[:200],
        "body": state.get("blog_excerpt", ""),
        "twitter_thread": state.get("twitter_thread", []),
        "source_briefing": state.get("briefing_path", ""),
    }

    save_dir = Path("data/articles")
    save_dir.mkdir(parents=True, exist_ok=True)
    save_path = save_dir / f"{article_id}.json"
    save_path.write_text(json.dumps(article, ensure_ascii=False, indent=2), encoding="utf-8")

    state["article"] = article
    state["saved_path"] = str(save_path)
    return state


def build_briefing_to_post_graph():
    """构建「简报 → 内容」工作流"""
    graph = StateGraph(BriefToPostState)
    graph.add_node("load_briefing", load_briefing)
    graph.add_node("extract", extract_headlines)
    graph.add_node("twitter", generate_twitter_thread)
    graph.add_node("blog", generate_blog_excerpt)
    graph.add_node("save", save_article)

    graph.set_entry_point("load_briefing")
    graph.add_edge("load_briefing", "extract")
    graph.add_edge("extract", "twitter")
    graph.add_edge("twitter", "blog")
    graph.add_edge("blog", "save")
    graph.add_edge("save", END)
    return graph.compile()


def generate_post_from_briefing(topic: str = "ai-agent") -> dict:
    """CLI 入口：从最新简报生成社交内容"""
    workflow = build_briefing_to_post_graph()
    result = workflow.invoke({
        "topic": topic,
        "briefing_path": "",
        "briefing_content": "",
        "headlines": [],
        "twitter_thread": [],
        "blog_excerpt": "",
        "article": {},
        "saved_path": "",
    })
    return {
        "article": result["article"],
        "saved_path": result["saved_path"],
        "briefing_path": result["briefing_path"],
        "headlines_count": len(result["headlines"]),
    }
