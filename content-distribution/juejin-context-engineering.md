# Context Engineering：比 Prompt Engineering 更重要的事

> 本文首发于 [王蕴的技术博客](https://walterhandsome.github.io/blog.html#context-engineering)，基于 [400+ 篇开源技术笔记](https://github.com/WalterHandsome/tech-learning-and-projects) 的深度分享。

## 前言

2025 年中，Shopify CEO Tobi Lütke 和前 OpenAI 研究员 Andrej Karpathy 几乎同时提出了一个观点：**Context Engineering 比 Prompt Engineering 更重要**。随后 Simon Willison 在博客中正式为这个概念定调。到了 2026 年，Context Engineering 已经成为 AI Agent 开发领域最核心的工程能力之一。

如果你还在纠结怎么写出更好的 Prompt，那你可能抓错了重点。

## 什么是 Context Engineering？

一句话定义：**Context Engineering 是设计和管理 LLM 在每次推理时所接收的完整信息载荷的工程实践。**

这个"信息载荷"不只是用户输入的那句话，它包括：

- **系统提示词（System Prompt）**：角色定义、行为约束、输出格式
- **对话历史（Conversation History）**：多轮交互的上下文
- **检索结果（Retrieved Context）**：RAG 系统返回的相关文档
- **工具定义（Tool Definitions）**：可调用的 Function Calling 接口
- **记忆（Memory）**：短期工作记忆和长期知识记忆
- **策略与规则（Policies）**：业务规则、安全约束、合规要求

> Prompt Engineering 问的是"我该对模型说什么"，Context Engineering 问的是"模型在回答之前，应该看到什么信息、什么时候看到、以什么格式看到"。

## 为什么 Prompt Engineering 不够了？

当你构建一个生产级 AI Agent 时，你会发现：

1. **上下文窗口是稀缺资源**：塞入过多无关信息会导致模型注意力被稀释
2. **Agent 需要跨步骤推理**：每一步需要的上下文完全不同，静态 Prompt 无法应对
3. **多源信息需要编排**：RAG 结果、工具返回值、用户偏好需要统一编排
4. **安全和合规要求**：需要控制模型能看到什么、不能看到什么

## Context Engineering 的四大支柱

### 1. 信息选择（What）

核心原则是**最小充分集**——找到让模型产生正确输出的最小高信号 token 集合。

```python
# 反面示例：把所有文档都塞进去
context = system_prompt + all_documents + all_history + all_tools

# 正面示例：精准选择相关信息
relevant_docs = rag_retrieve(query, top_k=3, threshold=0.8)
recent_history = conversation[-5:]
active_tools = select_tools(intent)
context = system_prompt + relevant_docs + recent_history + active_tools
```

### 2. 时序控制（When）

Agent 的执行是多步骤的，不同阶段需要不同的上下文：
- **意图识别阶段**：需要用户画像 + 历史行为
- **工具调用阶段**：需要工具 schema + 参数约束
- **结果生成阶段**：需要工具返回值 + 输出格式要求

### 3. 格式设计（How）

同样的信息，结构化呈现比纯文本堆砌效果好得多。

### 4. 容量管理（How Much）

实用策略：摘要压缩、优先级排序、动态裁剪、分层缓存。

## 实战代码

```python
def build_context(user_id: str, message: str) -> list:
    """为每次 LLM 调用动态构建上下文"""
    context = []

    # 第一层：系统角色与规则（固定）
    context.append({
        "role": "system",
        "content": load_system_prompt("customer_service_v3")
    })

    # 第二层：用户画像（从数据库实时获取）
    user_profile = get_user_profile(user_id)
    context.append({
        "role": "system",
        "content": format_user_profile(user_profile)
    })

    # 第三层：相关知识（RAG 检索）
    docs = rag_search(message, collection="faq", top_k=3)
    if docs:
        context.append({
            "role": "system",
            "content": format_retrieved_docs(docs)
        })

    # 第四层：对话历史（带摘要的滑动窗口）
    history = get_conversation_history(user_id, limit=10)
    if len(history) > 6:
        summary = summarize_history(history[:-4])
        context.append({"role": "system", "content": f"对话摘要：{summary}"})
        context.extend(history[-4:])
    else:
        context.extend(history)

    # 第五层：当前用户消息
    context.append({"role": "user", "content": message})

    return context
```

## 最佳实践

1. 建立上下文构建的标准化流水线
2. 对上下文做版本管理
3. 实施上下文的 A/B 测试
4. 监控 token 使用量和成本
5. 在上下文中加入"元信息"

## 写在最后

Context Engineering 是 Prompt Engineering 的自然演进。如果你正在构建 AI Agent，把"上下文设计"作为架构设计的核心环节，而不是事后补丁。

---

> 更多 AI Agent 学习笔记：[GitHub - tech-learning-and-projects](https://github.com/WalterHandsome/tech-learning-and-projects)（99 篇体系化笔记 + 2 个实战项目）
>
> 我的技术博客：[walterhandsome.github.io](https://walterhandsome.github.io/blog.html)
