"""配置管理"""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用配置，从环境变量和 .env 文件加载"""

    # LLM 配置
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    default_model: str = "claude-sonnet-4-20250514"

    # 知识库配置
    chroma_persist_dir: str = "./data/chroma_db"
    notes_dir: str = "./data/notes"

    # 平台 API
    github_token: str = ""
    juejin_cookie: str = ""
    twitter_bearer_token: str = ""
    zhihu_cookie: str = ""

    # 博客配置
    blog_repo: str = ""
    blog_file: str = "blog.html"

    # 推送配置
    bark_url: str = ""  # Bark 推送地址，格式 https://api.day.app/你的key

    # Postiz 配置（多平台分发）
    postiz_url: str = ""       # Postiz API 地址，如 http://localhost:5000
    postiz_api_key: str = ""   # Postiz API Key

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# 全局配置实例
settings = Settings()
