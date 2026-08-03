# 评论系统迁移（Valine → Giscus）实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将博客评论系统从已归档的 Valine/LeanCloud 切换到 Giscus（GitHub Discussions 后端）。

**Architecture:** 纯声明式配置改动，不写代码：`_config.butterfly.yml` 的 `comments.use` 改为 `Giscus`、填充 `giscus:` 段三个参数、删除 valine 段已失效凭据。主题内置 `giscus.pug` 模板负责渲染；侧边栏「最新评论」组件由主题逻辑（`card_newest_comment.pug:1` 排除 Giscus）自动隐藏。验证靠干净构建 + 构建产物 grep 检查 + 浏览器人工确认。

**Tech Stack:** Hexo 7.3 / Node 20、Butterfly 主题（submodule）、YAML 配置、Giscus（giscus.app client.js，CDN 加载）。无测试框架——验证方式是 `hexo generate` 产物检查 + 浏览器人工检查。

## Global Constraints

- 纯使用 Butterfly 主题内置能力，不引入任何自定义代码、CSS 或 JS。
- Giscus 参数（唯一真源，逐字使用）：`repo: li192863/li192863.github.io`、`repo_id: R_kgDOMEsqYw`、`category_id: DIC_kwDOMEsqY84DCi_i`。
- valine 段仅删除 `appId` / `appKey` / `serverURLs` 三行；段内其余键（`avatar`、`bg`、`visitor`、`option` 等）原样保留不改动。
- 除上述三段外，`_config.butterfly.yml` 其他任何配置不得改动（尤其 `comments.lazyload: true`、`comments.count: false`、`newest_comments` 段保持原值）。
- 不修改任何文章、页面内容；不做旧评论迁移。
- 每完成一个任务即提交一次；提交信息用中文，符合仓库现有风格。

---

### Task 1: 切换 `_config.butterfly.yml` 评论配置

**Files:**
- Modify: `_config.butterfly.yml:422`（`comments.use`）
- Modify: `_config.butterfly.yml:509-517`（`giscus:` 段）
- Modify: `_config.butterfly.yml:461-467`（`valine:` 段）

**Interfaces:**
- Consumes: 无（首个任务）
- Produces: 评论系统切换后的配置文件——Task 2 的构建产物检查依赖本任务的三个参数值

- [ ] **Step 1: 切换评论系统**

用 Edit 工具，`old_string: "use: Valine"`，`new_string: "use: Giscus"`（`_config.butterfly.yml` 第 422 行，该行是文件中唯一的 `use: Valine`）。

- [ ] **Step 2: 填充 giscus 段**

当前 giscus 段（第 509-517 行）为：

```yaml
giscus:
  repo:
  repo_id:
  category_id:
  theme:
    light: light
    dark: dark
  option:
```

用 Edit 工具，`old_string: "giscus:\n  repo:\n  repo_id:\n  category_id:"`，`new_string: "giscus:\n  repo: li192863/li192863.github.io\n  repo_id: R_kgDOMEsqYw\n  category_id: DIC_kwDOMEsqY84DCi_i"`。`theme` 与 `option` 保持不动。

- [ ] **Step 3: 删除 valine 段失效凭据**

当前 valine 段（第 461-467 行）为：

```yaml
valine:
  appId: 6WARa7siMPrLU8SHojz7CV9s-gzGzoHsz
  appKey: BeZnRzDEOZC3JEDkRW7emiUX
  avatar: monsterid # gravatar style https://valine.js.org/#/avatar
  serverURLs: https://6wara7si.lc-cn-n1-shared.com # This configuration is suitable for domestic custom domain name users, overseas version will be automatically detected (no need to manually fill in)
  bg: # valine background
  visitor: false
  option:
    placeholder: '留下你的足迹吧'
```

用 Edit 工具，`old_string` 为从 `appId: 6WARa7siMPrLU8SHojz7CV9s-gzGzoHsz` 到 `serverURLs:` 整行（含注释）的连续四行，`new_string` 为 `# appId: 6WARa7siMPrLU8SHojz7CV9s-gzGzoHsz (removed: archived LeanCloud app)` 单行注释——即用一行注释替代这四行，`avatar` 及其后各行保持不动。若 Edit 因 `#` 注释内容过长而不便，可改为直接删除四行（`new_string` 为空内容，仅保留结构）。两种方式任选，要求：`appId`/`appKey`/`serverURLs` 三个键值对及原注释不再存在于文件中，`avatar` 及之后键保持原样。

- [ ] **Step 4: 验证配置改动**

Run: `grep -nE "^(use|repo|repo_id|category_id|appId|appKey|serverURLs):" _config.butterfly.yml`
Expected:
- `use: Giscus`
- `repo: li192863/li192863.github.io`
- `repo_id: R_kgDOMEsqYw`
- `category_id: DIC_kwDOMEsqY84DCi_i`
- `appId:` / `appKey:` / `serverURLs:` 三个键**不再出现**

再 Run: `grep -c "Valine" _config.butterfly.yml`
Expected: `0`（`comments.use` 已切换；若 >0 检查是否有注释仍含 Valine 字样，注释属正常可忽略，但 `use: Valine` 不得再存在）。

- [ ] **Step 5: 提交**

```bash
git add _config.butterfly.yml
git commit -m "切换评论系统：Valine 迁移到 Giscus

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 干净构建 + 产物验证 + 人工检查

**Files:**
- 无新增/修改（只读验证；若验证发现问题，回到 Task 1 修复）

**Interfaces:**
- Consumes: Task 1 的三个 Giscus 参数值（`R_kgDOMEsqYw`、`DIC_kwDOMEsqY84DCi_i`）与 valine 旧凭据（`6WARa7siMPrLU8SHojz7CV9s-gzGzoHsz`）
- Produces: 验证通过的结论 + 待用户合并的最终 diff

- [ ] **Step 1: 干净构建（模拟 CI 全新 checkout）**

Run: `npm run clean && npm run build`
Expected: 无 ERROR，退出码 0。注意 `npm run clean` 会删除 `public/` 与 `db.json`（构建缓存），删除属正常。

- [ ] **Step 2: 产物中出现 Giscus 且参数正确**

Run: `grep -rl "giscus.app/client.js" public/ --include=index.html | head -5`
Expected: 输出文章页路径（形如 `public/<hash>/index.html`，含评论区的文章页）。再 Run:

```
grep -rn "R_kgDOMEsqYw" public/ | head -3
grep -rn "DIC_kwDOMEsqY84DCi_i" public/ | head -3
```

Expected: 两命令均有输出，且出自同一批文章页（`data-repo-id` 与 `data-category-id` 已渲染进页面）。

- [ ] **Step 3: 产物中无 Valine 残留**

Run: `grep -rn "6WARa7siMPrLU8SHojz7CV9s-gzGzoHsz\|6wara7si.lc-cn-n1-shared" public/`
Expected: 无任何输出（旧 appId/域名不出现于任何页面）。

- [ ] **Step 4: 「最新评论」组件不再渲染**

Run: `grep -rn "card-newest-comments" public/`
Expected: 无任何输出（主题渲染期已按 `comments.use: Giscus` 跳过该组件；若首页仍有输出说明配置未生效，回到 Task 1 检查）。

- [ ] **Step 5: 人工浏览器检查**

Run: `npm run server`，访问 http://localhost:4000 打开任一文章页，确认：
- 评论区显示 Giscus 评论框（「Sign in to comment」GitHub 登录按钮；登录后可发表评论）
- 侧边栏不再显示「最新评论」组件
- 明暗模式切换（页面右下角或导航栏切换按钮）时评论区主题跟随
- 浏览器控制台（F12 → Console）无报错

- [ ] **Step 6: 汇总结果**

向用户展示 `git log --oneline -2` 与 `git status`，说明改动范围；由用户决定合并分支 / push 到 `main`（CI 会自动构建部署，部署后线上再确认一次评论区加载）。此步不做任何提交（无新改动）。
