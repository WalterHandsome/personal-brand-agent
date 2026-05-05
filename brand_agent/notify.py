"""通知推送模块 - 支持 Bark（iOS 推送）"""

import httpx


def push_bark(bark_url: str, title: str, body: str, group: str = "AI简报") -> bool:
    """通过 Bark 推送通知到 iOS 设备

    Args:
        bark_url: Bark 推送地址，格式 https://api.day.app/你的key
        title: 通知标题
        body: 通知内容（支持 Markdown）
        group: 通知分组名称

    Returns:
        是否推送成功
    """
    url = bark_url.rstrip("/")
    try:
        resp = httpx.post(
            f"{url}/",
            json={
                "title": title,
                "body": body,
                "group": group,
                "icon": "https://github.githubassets.com/favicons/favicon.svg",
                "level": "timeSensitive",
            },
            timeout=10,
        )
        if resp.status_code == 200 and resp.json().get("code") == 200:
            print(f"✅ Bark 推送成功：{title}")
            return True
        print(f"❌ Bark 推送失败：{resp.text}")
        return False
    except Exception as e:
        print(f"❌ Bark 推送异常：{e}")
        return False


def format_briefing_for_bark(scored_items: list[dict], stats: dict) -> tuple[str, str]:
    """将简报数据格式化为 Bark 推送内容

    设计原则（参考 iOS 推送最佳实践）：
    - 标题 ≤ 40 字符，锁屏不截断
    - 正文展示 Top 3 要闻，每条 ≤ 80 字符
    - 底部附统计摘要，让用户知道还有更多

    Returns:
        (title, body) 元组
    """
    from datetime import datetime

    today = datetime.now().strftime("%m-%d")
    final_count = stats.get("final_count", 0)
    # 如果 stats 中没有 final_count，从 scored_items 长度推断
    if not final_count:
        final_count = len(scored_items)
    title = f"🤖 AI 简报 {today}｜{final_count} 条精选"

    lines = []
    for i, item in enumerate(scored_items[:3], 1):
        short_title = item.get("title", "")[:60]
        if len(item.get("title", "")) > 60:
            short_title += "…"
        score = item.get("score_total", 0)
        source = _bark_source_label(item.get("source", ""))
        lines.append(f"{i}. [{score}分] {short_title} ({source})")

    # 统计摘要
    raw_count = stats.get("raw_count", 0)
    if raw_count:
        lines.append(f"\n📊 采集 {raw_count} → 收录 {final_count}")

    if len(scored_items) > 3:
        lines.append(f"…共 {final_count} 条，详见完整简报")

    body = "\n".join(lines)
    return title, body


def _bark_source_label(source: str) -> str:
    """Bark 推送中的来源简称"""
    labels = {"hackernews": "HN", "github": "GH", "arxiv": "arXiv"}
    if source.startswith("rss:"):
        return source.replace("rss:", "")
    return labels.get(source, source)
