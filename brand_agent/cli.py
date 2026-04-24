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
def trending():
    """获取今日 AI 领域热点"""
    console.print(Panel("📡 获取今日热点", style="bold blue"))

    from brand_agent.agents.collector import collect_trending

    topics = collect_trending()

    table = Table(title="🔥 今日 AI 热点")
    table.add_column("来源", style="cyan")
    table.add_column("标题", style="white")
    table.add_column("热度", style="yellow")

    for topic in topics:
        table.add_row(topic["source"], topic["title"], topic["score"])

    console.print(table)


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
    """查看 Postiz 中已连接的社交媒体账号"""
    console.print(Panel("🔗 已连接的平台", style="bold blue"))

    from brand_agent.agents.distributor import list_channels

    integrations = list_channels()
    if not integrations:
        console.print("  ⚠️ 未配置 Postiz 或无已连接账号")
        console.print("  请先启动 Postiz 并在 .env 中配置 POSTIZ_URL 和 POSTIZ_API_KEY")
        return

    table = Table(title="Postiz 已连接平台")
    table.add_column("平台", style="cyan")
    table.add_column("账号", style="white")
    table.add_column("ID", style="dim")

    for item in integrations:
        if not item.get("disabled"):
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
