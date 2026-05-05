"""LLM 客户端工厂 - 统一的多后端 LLM 初始化逻辑

优先级：
1. AWS Bedrock（推荐）
2. Anthropic 直连 API
3. OpenAI API
4. 无配置 → 返回 None，调用方应 fallback 到规则实现
"""

from typing import Any, Optional


def create_llm(
    temperature: float = 0,
    timeout: int = 30,
    max_tokens: int = 2000,
) -> Optional[Any]:
    """创建 LLM 客户端

    Args:
        temperature: 采样温度，0 表示确定性输出
        timeout: 单次请求超时（秒）
        max_tokens: 最大输出 token 数

    Returns:
        LangChain BaseChatModel 实例，或 None（无配置时）
    """
    try:
        from brand_agent.config import settings
    except Exception:
        return None

    # 1. Bedrock（AWS 原生，推荐）
    if settings.aws_access_key_id and settings.bedrock_model_id:
        try:
            from langchain_aws import ChatBedrock
            return ChatBedrock(
                model=settings.bedrock_model_id,
                region_name=settings.aws_bedrock_region or settings.aws_region,
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"[LLM Factory] Bedrock 初始化失败，尝试其他后端: {e}")

    # 2. Anthropic 直连
    if settings.anthropic_api_key:
        try:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(
                model=settings.default_model,
                api_key=settings.anthropic_api_key,
                temperature=temperature,
                timeout=timeout,
                max_tokens=max_tokens,
            )
        except Exception as e:
            print(f"[LLM Factory] Anthropic 初始化失败，尝试其他后端: {e}")

    # 3. OpenAI
    if settings.openai_api_key:
        try:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(
                model="gpt-4o-mini",
                api_key=settings.openai_api_key,
                temperature=temperature,
                timeout=timeout,
            )
        except Exception as e:
            print(f"[LLM Factory] OpenAI 初始化失败: {e}")

    # 4. 无任何配置
    return None


def get_backend_name() -> str:
    """返回当前生效的 LLM 后端名称，用于日志/调试"""
    try:
        from brand_agent.config import settings
    except Exception:
        return "none"
    if settings.aws_access_key_id and settings.bedrock_model_id:
        return "bedrock"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return "none"
