# 🚀 Personal Brand Agent

> 用 AI Agent 自动化个人品牌运营：信息采集 → 内容生成 → 多平台分发 → 数据分析

## 项目简介

一个基于 LangGraph + MCP 的个人品牌自动化系统，帮助技术博主/开发者：

- 📡 **自动采集** AI 领域每日热点（Hacker News、GitHub Trending、arXiv）
- ✍️ **智能生成** 基于个人知识库的高质量技术文章
- 📤 **一键分发** 到多个平台（博客、掘金、Twitter/X、知乎）
- 📊 **数据追踪** 各平台表现，优化内容策略

## 架构设计

```
┌─────────────────────────────────────────────────────┐
│                Personal Brand Agent                  │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌────────────┐  ┌────────────┐  ┌──────────────┐  │
│  │  信息采集   │  │  内容生成   │  │  多平台分发   │  │
│  │   Agent    │  │   Agent    │  │    Agent     │  │
│  └─────┬──────┘  └─────┬──────┘  └──────┬───────┘  │
│        │               │                │           │
│  ┌─────▼───────────────▼────────────────▼────────┐  │
│  │              RAG 知识库（ChromaDB）              │  │
│  │         你的笔记 + 行业动态 + 历史文章            │  │
│  └───────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────┐  ┌────────────┐                     │
│  │  数据分析   │  │  选题规划   │                     │
│  │   Agent    │  │   Agent    │                     │
│  └────────────┘  └────────────┘                     │
│                                                      │
│  ┌───────────────────────────────────────────────┐  │
│  │           MCP Server 层（工具接口）              │  │
│  │  GitHub · 掘金 · Twitter · 知乎 · RSS · Web    │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## 技术栈

| 组件 | 技术选型 | 说明 |
|------|---------|------|
| Agent 框架 | LangGraph | 复杂工作流编排 |
| 知识库 | ChromaDB | 向量存储，笔记检索 |
| 工具协议 | MCP | 标准化工具调用 |
| LLM | Claude / GPT-4o | 内容生成 |
| 社交分发 | Postiz（可选） | 开源社交媒体调度 |
| CLI | Typer | 命令行交互 |
| 调度 | APScheduler | 定时任务 |

## 快速开始

```bash
# 克隆项目
git clone https://github.com/WalterHandsome/personal-brand-agent.git
cd personal-brand-agent

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp env.example .env
# 编辑 .env，填入你的 API Key

# 初始化知识库（导入你的笔记）
python -m brand_agent.cli init --notes-dir /path/to/your/notes

# 获取今日热点
python -m brand_agent.cli trending

# 生成博客文章
python -m brand_agent.cli generate --topic "Context Engineering"

# 多平台分发
python -m brand_agent.cli distribute --article latest --platforms blog,juejin,twitter
```

## 项目结构

```
personal-brand-agent/
├── brand_agent/
│   ├── __init__.py
│   ├── cli.py                  # CLI 入口
│   ├── config.py               # 配置管理
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── collector.py        # 信息采集 Agent
│   │   ├── writer.py           # 内容生成 Agent
│   │   ├── distributor.py      # 多平台分发 Agent
│   │   ├── analyzer.py         # 数据分析 Agent
│   │   └── planner.py          # 选题规划 Agent
│   ├── rag/
│   │   ├── __init__.py
│   │   ├── indexer.py          # 文档索引
│   │   └── retriever.py        # 检索器
│   ├── mcp_servers/
│   │   ├── __init__.py
│   │   ├── github_server.py    # GitHub MCP Server
│   │   ├── juejin_server.py    # 掘金 MCP Server
│   │   ├── twitter_server.py   # Twitter MCP Server
│   │   └── web_server.py       # Web 采集 MCP Server
│   ├── platforms/
│   │   ├── __init__.py
│   │   ├── base.py             # 平台基类
│   │   ├── blog.py             # 静态博客
│   │   ├── juejin.py           # 掘金
│   │   ├── twitter.py          # Twitter/X
│   │   └── zhihu.py            # 知乎
│   └── templates/
│       ├── blog_post.md        # 博客文章模板
│       ├── twitter_thread.md   # Twitter thread 模板
│       └── juejin_post.md      # 掘金文章模板
├── data/
│   ├── chroma_db/              # 向量数据库
│   └── articles/               # 生成的文章存档
├── tests/
├── env.example
├── requirements.txt
├── pyproject.toml
└── README.md
```

## 灵感来源

- [Postiz](https://github.com/gitroomhq/postiz-app) - 开源社交媒体调度工具，支持 19+ 平台
- [GBrain](https://github.com/garrytan/gbrain) - YC 总裁 Garry Tan 的 AI 记忆系统
- [ecrivai](https://github.com/ruankie/ecrivai) - LangChain 驱动的自动博客写手

## License

MIT
