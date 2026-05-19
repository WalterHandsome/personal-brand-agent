# 外部平台链接迁移清单

> 因 GitHub 用户名从 `WalterHandsome` 改为 `walterwang0x01`，所有外部平台贴过的旧链接都已 404，需要逐个更新。
> 本地仓库已自动替换完成，**只剩外部平台需要你手动操作**。

## URL 对照表

| 旧 URL | 新 URL | 备注 |
|---|---|---|
| `https://walterhandsome.github.io/` | `https://walterwang0x01.github.io/portfolio/` | 站点根 |
| `https://walterhandsome.github.io/portfolio/` | `https://walterwang0x01.github.io/portfolio/` | 主页（同上）|
| `https://walterhandsome.github.io/blog.html#xxx` | `https://walterwang0x01.github.io/portfolio/posts/xxx/` | ⚠️ 老锚点全部失效，新站是 Astro，按文章 slug 跳 |
| `https://walterhandsome.github.io/portfolio/briefing/` | `https://walterwang0x01.github.io/portfolio/briefing/` | 简报 |
| `https://walterhandsome.github.io/portfolio/rss.xml` | `https://walterwang0x01.github.io/portfolio/rss.xml` | RSS |
| `github.com/WalterHandsome/...` | `github.com/walterwang0x01/...` | GitHub 仓库（GitHub 会自动 301 重定向，但建议主动更新）|
| `@WalterHandsome` | `@walterwang0x01` | 社交 handle |

> ⚠️ **重点**：`/blog.html#锚点` 这种旧站链接全废，必须按文章 slug 重写，不能简单替换用户名。

## 待更新平台清单

### 1. 掘金（最优先）

#### 已发布文章里的回链需要修

打开掘金后台 → 我的文章 → 编辑每一篇 → 替换以下内容：

- 文章顶部"首发于"那段：
  - 旧：`本文首发于 [王蕴的技术博客](https://walterhandsome.github.io/blog.html#xxx)`
  - 新：`本文首发于 [Walter's Tech Blog](https://walterwang0x01.github.io/portfolio/posts/{文章 slug}/)`

- 文末"更多笔记"那段：
  - 旧：`https://github.com/WalterHandsome/tech-learning-and-projects`
  - 新：`https://github.com/walterwang0x01/tech-learning-and-projects`

- 个人简介里的博客链接：
  - 旧：`walterhandsome.github.io`
  - 新：`walterwang0x01.github.io/portfolio/`

#### 已知发布文章对照（参考 `content-distribution/juejin-context-engineering.md`）

| 文章 | 新博客地址（用这个替换 blog.html#xxx） |
|---|---|
| Context Engineering | `https://walterwang0x01.github.io/portfolio/posts/context-engineering-guide/` |

> 如果还有其他发到掘金的文章，按 `astro-site/src/content/blog/` 下的文件名（去掉 `.md`）做 slug，对应到 `/portfolio/posts/{slug}/`。

### 2. Twitter / X（参考 `content-distribution/twitter-threads.md`）

如果你已经发过这些 thread：

- thread 41 行：`github.com/walterwang0x01/tech-learning-and-projects`
- thread 90 行：`github.com/walterwang0x01/tech-learning-and-projects`
- thread 136 行：`github.com/walterwang0x01/tech-learning-and-projects`

X 平台**已发推不可编辑**，建议：
- 删除旧推重发，或
- 在原推下回复一条"链接已迁移到 walterwang0x01"做补救

### 3. 个人主页 / 简介（一次性更新）

逐个登录以下平台，更新个人简介和主页链接：

- [ ] **GitHub 个人主页**（`github.com/walterwang0x01` 的 README）
- [ ] **Twitter / X**：bio 里的链接
- [ ] **LinkedIn**：Contact info → Website
- [ ] **掘金**：个人主页 → 个人介绍
- [ ] **即刻**：个人主页 → 简介
- [ ] **知乎**：个人主页 → 编辑个人资料 → 个人简介
- [ ] **公众号**：自动回复、菜单链接、文章末尾的引导链接

### 4. RSS 订阅推广

老订阅者用旧 feed `https://walterhandsome.github.io/portfolio/rss.xml` 已经收不到新文章。

- [ ] 在 X、即刻等平台发一条公告："博客地址迁移到 walterwang0x01.github.io，请重新订阅 RSS"
- [ ] 把新 feed 提交到聚合站：[RSSHub](https://docs.rsshub.app/)、[Sub Stack](https://substack.com/)、[Telegram 频道] 等

### 5. 搜索引擎索引（被动等待）

Google / Bing 会逐步重新抓取，但你可以主动提交加速：

- [ ] **Google Search Console** → URL 检查 → 输入 `https://walterwang0x01.github.io/portfolio/sitemap.xml` → 请求编入索引
- [ ] **Bing Webmaster Tools** → 提交 sitemap

旧 URL 的索引会在几周内被 Google 标记为 404 自动剔除。

## 长期方案（强烈建议）

为了避免下一次改用户名 / 换平台时再次失链：

**买一个自己的域名做主入口**，比如 `walterwang.dev` / `0x01.dev` 等。

参考文档：`doc/custom-domain-setup.md`（同目录下）

---

## 自检 checklist

完成后逐项打钩：

- [ ] 掘金已发布文章里的"首发于"链接全部更新
- [ ] 掘金文章末尾的 GitHub 仓库链接更新
- [ ] 掘金个人简介更新
- [ ] X / Twitter bio 链接更新
- [ ] X / Twitter 关键 thread 已重发或评论补救
- [ ] LinkedIn 个人 website 更新
- [ ] 即刻、知乎、公众号简介更新
- [ ] 公众号自动回复 / 菜单链接更新
- [ ] Google Search Console 提交新 sitemap
- [ ] 在主流平台发一条"博客已迁移"公告
- [ ] 老订阅者引导切换 RSS

> 完成全部后，把这个文件归档到 `doc/archive/` 或者直接删掉。
