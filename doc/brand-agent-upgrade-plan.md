# Brand Agent 改造规划

> Author: Walter Wang
> 创建时间: 2026-05-05
> 目标：将 Brand Agent 升级为独立可用的简报采集 + 内容分发系统，不依赖 Kiro

## 背景

当前有两套简报系统：
1. **技术笔记 Kiro Hooks**：日常使用，依赖 Kiro IDE，采集质量高（LLM 判断 + Web Search）
2. **Brand Agent**：独立 Python 项目，可 CLI 运行，但采集功能弱、格式旧、只覆盖 AI 一个主题

改造目标：让 Brand Agent 成为 Kiro 不可用时的**完整备选方案**，同时发挥其内容生成 + 分发的独特价值。

## 改造范围

### Phase 1: 采集能力对齐（核心）

| 任务 | 说明 |
|------|------|
| 多主题支持 | 支持 `ai-agent` / `china-tech` / `global-tech` 三个主题 |
| 对齐采集源 | 复用 `briefing-tools.py` 的 RSS 源配置，或直接调用它 |
| Web Search 集成 | 集成 Tavily / SerpAPI / 或 DuckDuckGo 搜索补充 |
| 跨简报去重 | 三个主题之间互相去重 |
| 跨天去重 | 读取最近 3 天历史，避免重复 |
| LLM 评分 | 用 LLM 做内容质量判断，替代当前的关键词规则评分 |

### Phase 2: 简报格式更新

| 任务 | 说明 |
|------|------|
| 新模板 | 对齐 Kiro Hooks 的新格式（头条 + 快讯 + 项目 + 趋势） |
| 输出路径 | 改为 `output/briefings/{topic}/YYYY/MM/YYYY-MM-DD.md` |
| Bark 推送 | 修复收录数解析，对齐推送格式 |

### Phase 3: Postiz 部署 + 内容分发

| 任务 | 说明 |
|------|------|
| 部署 Postiz | Docker Compose 启动，复用现有 Redis（端口 6379） |
| 配置平台 | 在 Postiz Web UI 中连接 X/Twitter、LinkedIn 等账号 |
| 配置 .env | 填入 POSTIZ_URL 和 POSTIZ_API_KEY |
| 简报 → 内容 | 从简报自动生成 Twitter thread / 博客摘要 |
| 分发测试 | 实际发一条到 X/Twitter 验证全流程 |
| CLI 验证 | `python -m brand_agent.cli distribute` 和 `channels` 命令 |

**Postiz 部署预估资源：**
- Postiz 主应用（Node.js）：~200-400MB
- PostgreSQL：~100-200MB
- Redis：复用现有，不额外占用
- 总计新增：~300-600MB

### Phase 4: CLI 完善

| 任务 | 说明 |
|------|------|
| `trending` 命令 | 支持 `--topic` 参数选择主题 |
| `briefing` 命令 | 新增，对标 Kiro Hook 的完整流程 |
| `distribute` 命令 | 验证并修复 |
| 定时任务 | 可选：用 APScheduler 或 cron 每日自动执行 |

## 技术决策

### 方案 A：重写 collector.py
- 优点：完全自主，不依赖外部脚本
- 缺点：工作量大，和 briefing-tools.py 重复

### 方案 B：Brand Agent 调用 briefing-tools.py（推荐）
- 优点：复用已验证的采集逻辑，只需加 LLM 层
- 缺点：两个项目有耦合
- 实现：`subprocess.run(["python3", "path/to/briefing-tools.py", "collect", ...])` 或直接 import

### 方案 C：合并为一个项目
- 优点：消除重复
- 缺点：改动太大，影响现有工作流

**推荐方案 B**：Brand Agent 调用 briefing-tools.py 做采集+去重，自己负责 LLM 评分 + 格式生成 + 内容分发。

## 优先级

1. ⭐ Phase 2（格式更新）— 最快见效，30 分钟
2. ⭐ Phase 1（采集对齐）— 核心价值，2-3 小时
3. Phase 4（CLI 完善）— 体验优化，1 小时
4. Phase 3（分发验证）— 需要 Postiz 环境，时间不确定

## 执行方式

下次新对话时，带上这个文档作为上下文，按优先级逐步执行。
