---
inclusion: auto
description: Brand Agent 项目规范，包含编码原则、项目结构、技术栈约束
---

# Brand Agent 项目规范

## 编码四原则

> 基于 [andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) 适配本项目

### 1. 先想再写（Think Before Coding）

- 修改 Agent 逻辑前，先说明你理解的当前工作流是什么
- 涉及多个 Agent 协作的改动，先画出影响范围再动手
- 不确定某个 MCP Server 的接口行为时，先读代码确认

### 2. 简洁优先（Simplicity First）

- 这是一个演示 + 实用项目，不需要企业级抽象
- 不加没有要求的功能、配置项、错误处理
- 如果 50 行能解决，不要写 200 行
- 不要为"未来可能的需求"预留扩展点

### 3. 精准修改（Surgical Changes）

- 只改用户要求的部分，不顺手重构其他 Agent
- 改一个 Agent 时不要动其他 Agent 的代码
- 匹配现有代码风格，即使你觉得可以更好

### 4. 目标驱动（Goal-Driven Execution）

- 修 bug → 先描述如何复现，再修复，最后验证
- 加功能 → 先明确成功标准（输入什么、期望输出什么），再实现
- 重构 → 确保重构前后行为一致，用测试验证

## 项目结构

```
brand_agent/
├── agents/          # 各 Agent 实现（collector / writer / distributor / analyzer / planner）
├── rag/             # RAG 知识库（indexer + retriever）
├── mcp_servers/     # MCP Server 工具层
├── platforms/       # 平台分发适配器
├── templates/       # 内容模板
├── cli.py           # CLI 入口
└── config.py        # 配置管理
```

## 技术栈约束

- Python 3.10+，使用 type hints
- Agent 框架：LangGraph（不要引入 CrewAI 或其他框架）
- 向量存储：ChromaDB
- 工具协议：MCP
- CLI：Typer
- 代码风格：PEP 8，中文注释

## 语言规范

- 代码注释：中文
- 变量名 / 函数名 / 类名：英文
- Git commit message：英文，格式 `type: description`
- 文档和对话：中文
