"""CLI 入口 - 个人品牌 Agent 命令行工具"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Optional

app = typer.Typer(
    name="brand-agent",
    help="🚀 个人品牌 AI Agent - 信息采集 → 内容生成 → 多平台分发",
)
console = Console()


@app.command()
def init(
    notes_dir: str = typer.Option(
        "./data/notes", "--notes-dir", "-n", help="笔记目录路径"
    ),
):
    """初始化知识库，导入笔记文档"""
    console.print(Panel("📚 初始化知识库", style="bold blue"))

    from brand_agent.rag.indexer import build_index

    count = build_index(notes_dir)
    console.print(f"✅ 成功索引 [bold green]{count}[/] 篇文档")


@app.command()
def trending(
    topic: str = typer.Option(
        "ai-agent", "--topic", "-t",
        help="主题标识: ai-agent / china-tech / global-tech"
    ),
):
    """获取今日热点简报"""
    console.print(Panel(f"📡 获取今日热点 [{topic}]", style="bold blue"))

    from brand_agent.agents.collector import collect_trending

    result = collect_trending(topic=topic)
    items = result.get("items", [])
    stats = result.get("stats", {})

    table = Table(title=f"🔥 今日热点 [{topic}]")
    table.add_column("来源", style="cyan")
    table.add_column("标题", style="white")
    table.add_column("评分", style="yellow")

    for item in items[:15]:
        table.add_row(
            item.get("source", ""),
            item.get("title", "")[:70],
            str(item.get("score_total", 0)),
        )

    console.print(table)
    console.print(f"\n📊 采集 {stats.get('raw_count', 0)} 条 → 收录 {stats.get('final_count', 0)} 条")
    console.print(f"💾 简报已保存到 output/briefings/{topic}/")


@app.command()
def briefing(
    topics: str = typer.Option(
        "ai-agent,china-tech,global-tech", "--topics",
        help="逗号分隔的主题列表，默认全部三个主题",
    ),
):
    """一次采集多个主题简报（对标 Kiro Hook 的完整流程）

    三个主题按顺序采集，后采集的会基于前面的结果做跨简报去重。
    """
    topic_list = [t.strip() for t in topics.split(",") if t.strip()]
    console.print(Panel(f"📰 采集多主题简报: {', '.join(topic_list)}", style="bold blue"))

    from brand_agent.agents.collector import collect_trending, TOPIC_CONFIG

    summary_table = Table(title="📊 简报采集汇总")
    summary_table.add_column("主题", style="cyan")
    summary_table.add_column("原始", style="dim")
    summary_table.add_column("去重", style="dim")
    summary_table.add_column("跨简报", style="yellow")
    summary_table.add_column("收录", style="green")

    for topic in topic_list:
        if topic not in TOPIC_CONFIG:
            console.print(f"  ⚠️ 未知主题 [{topic}]，跳过")
            continue
        console.print(f"\n▶️  采集 [{topic}]...")
        result = collect_trending(topic=topic)
        stats = result.get("stats", {})
        summary_table.add_row(
            topic,
            str(stats.get("raw_count", 0)),
            str(stats.get("dedup_removed", 0)),
            str(stats.get("cross_topic_removed", 0)),
            str(stats.get("final_count", 0)),
        )

    console.print()
    console.print(summary_table)


@app.command("post-from-briefing")
def post_from_briefing(
    topic: str = typer.Option(
        "ai-agent", "--topic", "-t",
        help="主题: ai-agent / china-tech / global-tech",
    ),
):
    """从今日简报头条生成 Twitter Thread 和博客摘要

    生成的内容保存为标准 article 对象，可通过 `distribute` 命令发布。
    """
    console.print(Panel(f"✂️  从 [{topic}] 简报生成社交内容", style="bold blue"))

    from brand_agent.agents.briefing_to_post import generate_post_from_briefing

    result = generate_post_from_briefing(topic=topic)
    article = result["article"]

    if not result["briefing_path"]:
        console.print(f"  ⚠️ 未找到 [{topic}] 的简报文件，请先运行 `brand-agent trending -t {topic}`")
        return

    console.print(f"  📄 简报来源: {result['briefing_path']}")
    console.print(f"  📌 头条数量: {result['headlines_count']}")
    console.print(f"  🐦 Twitter Thread: {len(article.get('twitter_thread', []))} 条推文")
    console.print(f"  💾 已保存到: {result['saved_path']}")
    console.print(f"\n  下一步: [bold cyan]brand-agent distribute -a {article['id']} -p x[/]")


@app.command()
def generate(
    topic: str = typer.Option(..., "--topic", "-t", help="文章主题"),
    style: str = typer.Option(
        "blog", "--style", "-s", help="输出风格: blog/twitter/juejin"
    ),
):
    """基于知识库生成技术文章"""
    console.print(Panel(f"✍️ 生成文章: {topic}", style="bold blue"))

    from brand_agent.agents.writer import generate_article

    article = generate_article(topic=topic, style=style)

    console.print(Panel(article["title"], style="bold green"))
    console.print(f"📝 字数: {len(article['body'])}")
    console.print(f"🏷️ 标签: {', '.join(article['tags'])}")
    console.print(f"💾 已保存到: {article['saved_path']}")


@app.command()
def distribute(
    article: str = typer.Option(
        "latest", "--article", "-a", help="文章 ID 或 'latest'"
    ),
    platforms: str = typer.Option(
        "x", "--platforms", "-p",
        help="Postiz 平台标识，逗号分隔: x,linkedin,bluesky,medium,threads 等"
    ),
):
    """将文章通过 Postiz 分发到多个平台"""
    platform_list = [p.strip() for p in platforms.split(",")]
    console.print(
        Panel(f"📤 分发文章到: {', '.join(platform_list)}", style="bold blue")
    )

    from brand_agent.agents.distributor import distribute_article

    results = distribute_article(article_id=article, platforms=platform_list)

    for platform, result in results.items():
        status = "✅" if result["success"] else "❌"
        console.print(f"  {status} {platform}: {result['message']}")


@app.command()
def channels():
    """查看 Postiz 连通性和已连接的社交媒体账号"""
    console.print(Panel("🔗 Postiz 健康检查 & 已连接平台", style="bold blue"))

    from brand_agent.config import settings

    if not settings.postiz_url or not settings.postiz_api_key:
        console.print("  ⚠️ Postiz 未配置")
        console.print("  请在 .env 中设置 POSTIZ_URL（如 http://localhost:5000）和 POSTIZ_API_KEY")
        return

    # 健康检查
    from brand_agent.platforms.postiz import PostizClient
    client = PostizClient(settings.postiz_url, settings.postiz_api_key)
    ok, msg = client.health_check()
    status_icon = "✅" if ok else "❌"
    console.print(f"  {status_icon} Postiz [{settings.postiz_url}]: {msg}")

    if not ok:
        return

    # 列出绑定的平台
    from brand_agent.agents.distributor import list_channels
    try:
        integrations = list_channels()
    except Exception as e:
        console.print(f"  ❌ 获取平台列表失败: {e}")
        return

    enabled = [i for i in integrations if not i.get("disabled")]
    if not enabled:
        console.print("  ⚠️ Postiz 连通但未绑定任何平台账号")
        console.print("  请在 Postiz Web UI 中绑定至少一个社交账号")
        return

    table = Table(title="Postiz 已连接平台")
    table.add_column("平台", style="cyan")
    table.add_column("账号", style="white")
    table.add_column("ID", style="dim")

    for item in enabled:
        table.add_row(
            item.get("providerIdentifier", ""),
            item.get("name", ""),
            item.get("id", "")[:12] + "...",
        )

    console.print(table)


@app.command()
def plan(
    weeks: int = typer.Option(1, "--weeks", "-w", help="规划周数"),
):
    """生成内容选题规划"""
    console.print(Panel(f"📋 生成 {weeks} 周选题规划", style="bold blue"))

    from brand_agent.agents.planner import generate_plan

    plan = generate_plan(weeks=weeks)

    for week in plan:
        console.print(f"\n[bold]📅 第 {week['week']} 周[/]")
        for item in week["topics"]:
            console.print(f"  • {item['title']} [{item['platform']}]")


@app.command()
def stats():
    """查看各平台数据统计"""
    console.print(Panel("📊 数据统计", style="bold blue"))

    from brand_agent.agents.analyzer import get_stats

    data = get_stats()

    table = Table(title="📈 各平台表现")
    table.add_column("平台", style="cyan")
    table.add_column("文章数", style="white")
    table.add_column("总阅读", style="green")
    table.add_column("总点赞", style="yellow")

    for platform, stat in data.items():
        table.add_row(
            platform,
            str(stat["articles"]),
            str(stat["views"]),
            str(stat["likes"]),
        )

    console.print(table)


if __name__ == "__main__":
    app()
