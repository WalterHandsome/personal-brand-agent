# Twitter/X Thread 版本

## Thread 1: Context Engineering

🧵 为什么 Prompt Engineering 已经不够了？聊聊 2026 年最重要的 AI 技能：Context Engineering

1/ Shopify CEO Tobi Lütke 和 Andrej Karpathy 几乎同时说了一件事：Context Engineering 比 Prompt Engineering 更重要。

这不是换个名字炒概念，而是一个根本性的思维转变 👇

2/ Prompt Engineering 问的是："我该对模型说什么？"

Context Engineering 问的是："模型在回答之前，应该看到什么信息、什么时候看到、以什么格式看到？"

这是从写一句话，升级到设计一个系统。

3/ 一个生产级 AI Agent 的上下文包含：
- System Prompt（角色定义）
- 对话历史（多轮交互）
- RAG 检索结果（相关文档）
- 工具定义（Function Calling）
- 记忆（短期+长期）
- 业务规则和安全约束

这些都需要动态编排，不是一个 Prompt 能搞定的。

4/ Context Engineering 四大支柱：
① What - 模型需要看到哪些信息？（最小充分集）
② When - 信息在什么时候注入？（分步骤动态组装）
③ How - 以什么格式呈现？（结构化 > 纯文本堆砌）
④ How Much - 如何管理上下文窗口容量？

5/ 最常见的误区：上下文越长越好。

实际上，过长的上下文会让模型"迷路"。关键是找到最小的高信号 token 集合，让模型产生正确输出。

6/ 如果你在做 AI Agent 开发，从今天开始把"上下文设计"作为架构设计的核心环节。

我写了一篇完整的深度文章，包含实战代码示例 👇
[博客链接]

更多 AI Agent 学习笔记：github.com/WalterHandsome/tech-learning-and-projects

---

## Thread 2: MCP 协议

🧵 MCP 协议到底是什么？为什么它被叫做 AI Agent 的「USB 接口」？

一个 thread 讲清楚 👇

1/ MCP（Model Context Protocol）是 Anthropic 提出的开放协议，定义了 LLM 应用如何与外部工具进行标准化通信。

简单说：它让 AI Agent 能用统一的方式调用任何工具。

2/ MCP 之前的问题：M 个 AI 应用 × N 个工具 = M×N 个定制集成

MCP 之后：M 个 Client + N 个 Server = M+N

就像 USB 统一了外设接口一样，MCP 统一了 AI 工具接口。

3/ MCP Server 提供三种能力：
🔧 Tools - 可执行的操作（发邮件、查数据库）
📄 Resources - 可读取的数据（文件、记录）
💬 Prompts - 预定义的交互模板

4/ 用 Python 写一个 MCP Server 只需要几十行代码：

```python
from mcp.server.fastmcp import FastMCP
mcp = FastMCP("my-tools")

@mcp.tool()
def search_notes(query: str) -> str:
    """搜索技术笔记"""
    return vector_db.search(query)
```

就这么简单。

5/ 到 2026 年，Kiro、Cursor、Claude Desktop 等主流工具都原生支持 MCP。

Cloudflare、Stripe、Shopify 都提供了官方 MCP Server。

生态已经起来了。

6/ 完整的 MCP 深度解析文章 👇
[博客链接]

99 篇 AI Agent 体系化学习笔记：github.com/WalterHandsome/tech-learning-and-projects

---

## Thread 3: AI Agent 框架选型

🧵 LangGraph vs CrewAI vs OpenAI SDK，到底该选哪个？

基于实际项目经验的选型指南 👇

1/ 一句话总结：
- LangGraph = 精细控制（有向图）
- CrewAI = 快速协作（角色扮演）
- OpenAI SDK = 极简主义（三个概念）

2/ 选 LangGraph 如果你需要：
✅ 复杂多步骤工作流
✅ 人工审批节点
✅ 状态持久化和恢复
✅ 精细的流程控制

学习曲线最高，但生产就绪度也最高。

3/ 选 CrewAI 如果你需要：
✅ 多角色协作
✅ 快速出原型
✅ 内容生成流水线
✅ 10 分钟跑起来

上手最快，代码最直觉。

4/ 选 OpenAI SDK 如果你需要：
✅ 极简 API
✅ 深度 OpenAI 生态集成
✅ 快速原型验证

概念最少，但灵活性也最低。

5/ 我的实战选择：
- 复杂工作流项目 → LangGraph
- 内容创作流水线 → CrewAI

没有最好的框架，只有最适合场景的框架。

完整对比文章 👇 [博客链接]

框架笔记 + 实战项目：github.com/WalterHandsome/tech-learning-and-projects
