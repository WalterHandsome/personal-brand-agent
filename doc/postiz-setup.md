# Postiz 本地部署指南

> Author: Walter Wang
> 创建时间: 2026-05-05

Postiz 是 Brand Agent 的多平台分发后端，通过 Docker Compose 在本地启动。本指南覆盖首次部署、绑定 X 账号、生成 API Key 全流程。

## 资源需求

| 项 | 最低 | 推荐 |
| --- | --- | --- |
| RAM | 2 GB | 4 GB |
| 磁盘 | 3 GB | 5 GB |
| CPU | 2 vCPU | 2 vCPU |

完整栈有 7 个容器：`postiz` + `postiz-postgres` + `postiz-redis` + Temporal 工作流的 4 个组件。

## 前置条件

- 已安装 Docker Desktop 或 Docker Engine + docker-compose v2
- 已在 `🤖 Brand Agent/.env` 中保留 `POSTIZ_URL=http://localhost:5000`（Brand Agent 现有默认值）

## 步骤 1：准备配置文件

```bash
cd "🤖 Brand Agent"

# 复制 Postiz 专属环境变量模板
cp .env.postiz.example .env.postiz

# 生成一个强随机 JWT_SECRET（至少 48 字符）
python3 -c "import secrets; print(secrets.token_urlsafe(48))"

# 将输出粘贴到 .env.postiz 的 JWT_SECRET=
```

**重要**：X/Twitter 平台凭证（`X_API_KEY` / `X_API_SECRET`）在启动前不是必须的，但想在 Postiz UI 里绑定 X 账号时必须先填好。X 凭证申请步骤见文末附录。

## 步骤 2：启动 Postiz

```bash
# 首次启动会下载 5-10 个镜像（约 3GB），耗时 5-10 分钟
docker compose -f docker-compose.postiz.yml up -d

# 查看启动状态
docker compose -f docker-compose.postiz.yml ps

# 跟踪 Postiz 主容器日志
docker compose -f docker-compose.postiz.yml logs -f postiz
```

看到 `Nest application successfully started` 说明后端就绪。

等待所有健康检查通过后访问：**http://localhost:5000**

## 步骤 3：创建账号并生成 API Key

1. 打开 http://localhost:5000
2. 点击 Sign Up，用邮箱注册一个管理员账号
3. 登录后进入 `Settings` → `Developers` → `Public API`
4. 点击 `Generate API Key`，复制生成的 Key
5. 填回 Brand Agent 的 `.env`：

   ```ini
   POSTIZ_URL=http://localhost:5000
   POSTIZ_API_KEY=<刚才生成的 Key>
   ```

## 步骤 4：验证连通性

```bash
brand-agent channels
```

预期输出：

```
✅ Postiz [http://localhost:5000]: API 连通，认证通过
⚠️ Postiz 连通但未绑定任何平台账号
请在 Postiz Web UI 中绑定至少一个社交账号
```

## 步骤 5：绑定 X/Twitter 账号

先确保 `.env.postiz` 中 `X_API_KEY` 和 `X_API_SECRET` 已填好，然后：

```bash
docker compose -f docker-compose.postiz.yml restart postiz
```

在 Postiz UI 里：

1. 左侧菜单 → `Channels` → `Add Channel`
2. 选择 `X (Twitter)`
3. 跳转到 X 授权页，登录并授权
4. 回到 Postiz，看到 X 账号出现在已连接列表

再跑一次 `brand-agent channels`，应该能看到平台列表中出现 X。

## 步骤 6：端到端分发测试

```bash
# 先生成内容
brand-agent post-from-briefing -t ai-agent

# 真实发布到 X
brand-agent distribute -a briefing-ai-agent-2026-05-05 -p x
```

成功会看到：

```
✅ x: 已发布到 x
```

## 常见问题

### 启动失败：`bind: address already in use`

已被占用的端口：5000（Postiz Web）、7233（Temporal gRPC）、8080（Temporal UI）。

找出占用进程：

```bash
lsof -iTCP:5000 -sTCP:LISTEN
```

关掉占用进程，或修改 `docker-compose.postiz.yml` 里对应的 `ports` 映射（同时更新 Brand Agent `.env` 的 `POSTIZ_URL`）。

### Temporal 启动慢/失败

Temporal 依赖 Elasticsearch，首次启动需要 1-2 分钟。如果超过 5 分钟还没就绪：

```bash
docker compose -f docker-compose.postiz.yml logs temporal-elasticsearch
docker compose -f docker-compose.postiz.yml logs temporal
```

内存不足是常见原因（Elasticsearch 需要 512MB+）。确认 Docker Desktop 的内存配额 ≥ 4GB。

### 忘记账号密码

清库重来：

```bash
docker compose -f docker-compose.postiz.yml down -v
docker compose -f docker-compose.postiz.yml up -d
```

⚠️ `-v` 会删除所有数据卷，包括已绑定的社交账号。

## 停止 & 清理

```bash
# 停止（保留数据，可再次启动）
docker compose -f docker-compose.postiz.yml down

# 停止并清空数据
docker compose -f docker-compose.postiz.yml down -v

# 清理未使用的镜像（释放磁盘）
docker image prune -a
```

## 附录：申请 X/Twitter API 凭证

1. 登录 [X Developer Portal](https://developer.twitter.com/)
2. 如果还没有开发者账号，申请 Free 账号（免费，支持每月 500 条推文）
3. Dashboard → Projects & Apps → `+ New App`
4. App 创建后在 `Keys and Tokens` 标签页：
   - `API Key` → 填入 `X_API_KEY`
   - `API Key Secret` → 填入 `X_API_SECRET`
5. User authentication settings → 开启 `OAuth 1.0a`，Callback URL 填 `http://localhost:5000/integrations/social/x`
6. App permissions → 选择 `Read and write`

## 相关文档

- [Postiz 官方 Docker Compose 文档](https://docs.postiz.com/installation/docker-compose)
- [Postiz Public API 文档](https://docs.postiz.com/public-api)
- [Brand Agent 改造规划](./brand-agent-upgrade-plan.md)
