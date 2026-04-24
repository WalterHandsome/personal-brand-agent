"""Postiz API 客户端 - 通过本地 Postiz 实例发布到多个社交平台

Postiz 是一个开源的社交媒体调度工具，本地 Docker 启动后暴露 REST API。
文档：https://docs.postiz.com/public-api
"""

from datetime import datetime, timezone
from typing import Optional

import httpx


class PostizClient:
    """Postiz REST API 客户端"""

    def __init__(self, api_url: str, api_key: str):
        """
        Args:
            api_url: Postiz API 地址，如 http://localhost:5000
            api_key: Postiz API Key（Settings > Developers > Public API）
        """
        self.base_url = api_url.rstrip("/")
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    def list_integrations(self) -> list[dict]:
        """获取所有已连接的社交媒体账号"""
        resp = httpx.get(
            f"{self.base_url}/public/v1/integrations",
            headers=self.headers,
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json()

    def find_integration(self, provider: str) -> Optional[dict]:
        """按平台名称查找已连接的账号

        Args:
            provider: 平台标识，如 x, linkedin, bluesky, medium, reddit 等
        """
        integrations = self.list_integrations()
        for item in integrations:
            if item.get("providerIdentifier") == provider and not item.get("disabled"):
                return item
        return None

    def create_post(
        self,
        integration_id: str,
        provider: str,
        content: str | list[str],
        post_type: str = "now",
        schedule_date: Optional[str] = None,
        settings: Optional[dict] = None,
    ) -> dict:
        """创建并发布/排期一条帖子

        Args:
            integration_id: 平台连接 ID（从 list_integrations 获取）
            provider: 平台标识（x, linkedin, bluesky 等）
            content: 帖子内容，字符串或字符串列表（用于 Thread）
            post_type: 发布类型 - now（立即）/ schedule（排期）/ draft（草稿）
            schedule_date: 排期时间（UTC ISO 格式），post_type=schedule 时必填
            settings: 平台特定设置，不传则使用默认值
        """
        # 构建 value 数组（支持 Thread）
        if isinstance(content, str):
            value = [{"content": content, "image": []}]
        else:
            value = [{"content": c, "image": []} for c in content]

        # 平台设置
        if settings is None:
            settings = {"__type": provider}
        elif "__type" not in settings:
            settings["__type"] = provider

        # 发布时间
        if post_type == "schedule" and not schedule_date:
            raise ValueError("排期发布需要提供 schedule_date")
        date = schedule_date or datetime.now(timezone.utc).isoformat()

        payload = {
            "type": post_type,
            "date": date,
            "shortLink": False,
            "tags": [],
            "posts": [
                {
                    "integration": {"id": integration_id},
                    "value": value,
                    "settings": settings,
                }
            ],
        }

        resp = httpx.post(
            f"{self.base_url}/public/v1/posts",
            headers=self.headers,
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def publish_now(
        self,
        provider: str,
        content: str | list[str],
        settings: Optional[dict] = None,
    ) -> dict:
        """立即发布到指定平台（自动查找 integration）

        Args:
            provider: 平台标识
            content: 帖子内容
            settings: 平台特定设置

        Returns:
            发布结果

        Raises:
            ValueError: 未找到该平台的连接
        """
        integration = self.find_integration(provider)
        if not integration:
            raise ValueError(f"未找到已连接的 {provider} 账号，请先在 Postiz 中绑定")

        return self.create_post(
            integration_id=integration["id"],
            provider=provider,
            content=content,
            post_type="now",
            settings=settings,
        )
