# 自定义域名接入 GitHub Pages 完整指南

> 让你的博客 URL 从 `https://walterwang0x01.github.io/portfolio/` 变成 `https://你的域名.com/`，永远不再受 GitHub 用户名变更影响。

## 为什么强烈建议接入

你已经踩过一次"改 GitHub 用户名导致全网链接失效"的坑了。**自定义域名是这个问题的终极解法**：

- 域名是你自己的资产，跟着你走
- 未来 GitHub 用户名再改、迁移到 Vercel/Netlify、换博客系统，**外部链接永远不变**
- 看起来更专业（`yourname.com` vs `walterwang0x01.github.io/portfolio/`）
- 成本低：约 ¥75-150/年（10-20 美元/年）

## 第一步：选域名

### 推荐域名（按性价比 / 调性）

| 域名 | 估价/年 | 适合调性 | 是否可注册（之前查过的）|
|---|---|---|---|
| `walteryunwang.com` | ~¥75 | 真名派、专业 | ✅ 可注册 |
| `waltyunwang.com` | ~¥75 | 真名派、稍短 | ✅ 可注册 |
| `waltyun.com` | ~¥75 | 真名派、极简 | ✅ 可注册 |
| `walterwang.dev` | ~¥150 | 开发者向 | ⚠️ 需现场查 |
| `0x01.dev` / `0x01.io` | ~¥150-300 | 极客向，呼应你的 ID 后缀 | ⚠️ 需现场查 |

> `.com` 最稳，国际、所有人都认；`.dev` 自带 HTTPS 强制，对开发者品牌加分。

### 在哪买（按推荐度）

1. **Cloudflare Registrar**（最推荐⭐）
   - 几乎按成本价（无溢价）
   - 自带 Cloudflare DNS 和 CDN
   - 网址：https://dash.cloudflare.com/
   - 缺点：要先注册 Cloudflare 账号

2. **Porkbun**
   - 价格友好，UI 干净
   - 自带免费 WHOIS 隐私保护
   - 网址：https://porkbun.com/

3. **阿里云万网 / 腾讯云**（国内备案场景）
   - 国内访问解析快
   - 但 GitHub Pages 不需要备案（境外服务）

4. **GoDaddy / Namecheap**
   - 老牌但溢价多，**不推荐**

### 买完之后立刻要做的事

- [ ] 开启 **WHOIS 隐私保护**（防止个人信息暴露）
- [ ] 开启 **域名锁定**（防止误删/被盗转出）
- [ ] 开启 **自动续费**（防止过期被抢注）

## 第二步：配置 DNS

假设你买的域名是 `walteryunwang.com`，并且想用根域名 `walteryunwang.com` + `www.walteryunwang.com` 都指向 GitHub Pages。

### 在域名服务商的 DNS 设置里添加以下记录

| 类型 | 主机记录 | 记录值 | TTL |
|---|---|---|---|
| **A** | `@` | `185.199.108.153` | 600 |
| **A** | `@` | `185.199.109.153` | 600 |
| **A** | `@` | `185.199.110.153` | 600 |
| **A** | `@` | `185.199.111.153` | 600 |
| **AAAA** | `@` | `2606:50c0:8000::153` | 600 |
| **AAAA** | `@` | `2606:50c0:8001::153` | 600 |
| **AAAA** | `@` | `2606:50c0:8002::153` | 600 |
| **AAAA** | `@` | `2606:50c0:8003::153` | 600 |
| **CNAME** | `www` | `walterwang0x01.github.io` | 600 |

> 这 4 个 A 记录和 4 个 AAAA 记录是 GitHub Pages 官方 IP，[官方文档来源](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site/managing-a-custom-domain-for-your-github-pages-site#configuring-an-apex-domain)。

### 验证 DNS 生效

DNS 通常 5 分钟到几小时生效。验证命令：

```bash
# 验证 A 记录
dig walteryunwang.com +short

# 应该看到 4 个 GitHub IP：
# 185.199.108.153
# 185.199.109.153
# 185.199.110.153
# 185.199.111.153

# 验证 CNAME
dig www.walteryunwang.com +short
# 应该看到：walterwang0x01.github.io.
```

## 第三步：在 GitHub 仓库配置自定义域名

### 操作步骤

1. 打开仓库：https://github.com/walterwang0x01/portfolio
2. **Settings** → **Pages**
3. 在 **Custom domain** 输入框里输入：`walteryunwang.com`（不要带 `https://` 和斜杠）
4. 点 **Save**
5. 等几分钟，GitHub 会自动验证 DNS 配置
6. 验证通过后，**勾选 Enforce HTTPS**（强制启用 HTTPS，免费 SSL 证书自动签发）

### 仓库根目录会自动出现 `CNAME` 文件

GitHub 会自动在你的仓库根目录提交一个 `CNAME` 文件，内容是 `walteryunwang.com`。

但因为你的项目用 Astro 部署到 `astro-site/dist`，需要把 CNAME 写到 `astro-site/public/` 目录，让构建后被复制到 dist 根目录：

```bash
echo "walteryunwang.com" > astro-site/public/CNAME
git add astro-site/public/CNAME
git commit -m "feat: add custom domain CNAME"
git push
```

## 第四步：调整 Astro 配置

### 必须改的：`astro-site/astro.config.mjs`

```js
export default defineConfig({
  // 改前：
  // site: 'https://walterwang0x01.github.io',
  // base: '/portfolio',
  
  // 改后（接入自定义域名后，base 必须去掉，否则路径会变成 walteryunwang.com/portfolio/）：
  site: 'https://walteryunwang.com',
  base: '/',  // 或者直接删除这一行（Astro 默认就是 '/'）
  // ...
});
```

### 全局清理 `/portfolio/` 路径引用

接入自定义域名后，所有 `/portfolio/xxx` 的路径都要改成 `/xxx`，包括但不限于：

- `astro-site/src/components/AuthorCard.astro`：RSS、简报链接
- `astro-site/src/layouts/BaseLayout.astro`：BASE_URL 默认值
- `astro-site/src/pages/rss.xml.ts`：base 注释
- `.kiro/steering/blog-conventions.md`：cover 路径示例

> 这一步比较繁琐，到时候可以让 Kiro 帮你做一次全局替换。

### 同步更新所有外部引用的 URL

把所有指向 `https://walterwang0x01.github.io/portfolio/` 的地方都改成 `https://walteryunwang.com/`：

- `index.html`、`briefing.html` 的 og:url、canonical
- `rss.xml`、`sitemap.xml` 里所有 link
- `robots.txt` 里的 sitemap 路径
- `astro-site/public/robots.txt`
- `personal-brand-agent/env.example` 的 `BLOG_REPO`（注意这个不需要改）

## 第五步：验证

部署完成后，依次访问以下 URL，确认全部 200：

- https://walteryunwang.com/
- https://walteryunwang.com/briefing/
- https://walteryunwang.com/rss.xml
- https://walteryunwang.com/sitemap.xml

并且 https://www.walteryunwang.com/ 应该自动重定向到 https://walteryunwang.com/。

## 风险与注意事项

### 1. 域名续费

域名是按年付的。**一旦过期且没续费，可能在几周内被别人抢注**。一定开自动续费，并把信用卡续费提醒打开。

### 2. DNS 切换会有 5-30 分钟空档期

切换 DNS 期间，你的访客可能短暂访问不到。建议**周末凌晨**切换，影响最小。

### 3. 旧 GitHub Pages URL 仍然可用

接入自定义域名后，`walterwang0x01.github.io/portfolio/` 仍然能访问，但会自动重定向到自定义域名。**不会同时存在两份内容**。

### 4. Google 索引迁移

接入自定义域名后，记得在 Google Search Console 里：

- 添加新域名 `walteryunwang.com` 作为新资源
- 提交新的 sitemap：`https://walteryunwang.com/sitemap.xml`
- 旧域名 `walterwang0x01.github.io` 可以保留监控状态，等 Google 自动迁移

### 5. RSS 订阅迁移

老订阅者用旧 RSS 会自动跟着重定向到新 URL，但建议明示：

在 RSS feed 里加一个置顶 item："博客已迁移到 walteryunwang.com，本 feed 仍可用但建议更新订阅地址"。

---

## 完整 checklist

按顺序执行：

### 域名采购阶段
- [ ] 选好域名（推荐 `walteryunwang.com`）
- [ ] 在 Cloudflare Registrar / Porkbun 注册
- [ ] 开启 WHOIS 隐私、域名锁定、自动续费

### DNS 配置阶段
- [ ] 添加 4 个 A 记录指向 GitHub Pages
- [ ] 添加 4 个 AAAA 记录（IPv6 支持）
- [ ] 添加 CNAME 记录 `www` → `walterwang0x01.github.io`
- [ ] `dig` 命令验证 DNS 生效

### GitHub 配置阶段
- [ ] 仓库 Settings → Pages → Custom domain 填入域名并保存
- [ ] 等 GitHub 验证 DNS（约 5-30 分钟）
- [ ] 勾选 Enforce HTTPS
- [ ] 在 `astro-site/public/CNAME` 写入域名

### Astro 配置阶段
- [ ] `astro.config.mjs` 改 `site` 和去掉 `base: '/portfolio'`
- [ ] 全局替换所有 `/portfolio/` 路径引用
- [ ] 全局替换所有 `walterwang0x01.github.io/portfolio` 为新域名
- [ ] `npm run build` 本地验证通过
- [ ] commit + push

### 验证阶段
- [ ] 访问 `https://你的域名/` 应为 200
- [ ] 访问 `https://你的域名/briefing/` 应为 200
- [ ] HTTPS 证书有效（浏览器锁标志）
- [ ] `www.你的域名` 自动 301 重定向到根域名

### SEO 与外部更新
- [ ] Google Search Console 添加新资源、提交 sitemap
- [ ] 各社交平台 bio 更新为新域名
- [ ] 发一条公告通知关注者
