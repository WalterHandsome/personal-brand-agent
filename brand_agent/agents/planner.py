"""选题规划 Agent - 结合热点趋势和知识库生成选题建议"""


def generate_plan(weeks: int = 1) -> list[dict]:
    """生成内容选题规划

    TODO: 接入 LLM，结合以下信息生成选题：
    1. 近期 AI 领域热点趋势
    2. 知识库中尚未写过的主题
    3. 历史文章的表现数据
    4. 各平台的内容偏好
    """
    # 骨架实现：返回示例选题
    plan = []
    for w in range(1, weeks + 1):
        plan.append({
            "week": w,
            "topics": [
                {
                    "title": "待 LLM 生成选题",
                    "platform": "blog + juejin",
                    "priority": "high",
                    "reason": "基于热点趋势和知识库分析",
                },
            ],
        })
    return plan
