# 评论系统迁移：Valine → Giscus — 设计文档

日期：2026-08-03
状态：已批准

## 背景与目标

博客评论使用 Valine（`_config.butterfly.yml` `comments.use: Valine`），后端为 LeanCloud 应用 `6WARa7si...`。该应用已被 LeanCloud 归档（API 返回 `Code 504: The app is archived`），评论功能失效。LeanCloud 免费版长期不活跃会触发归档，依赖其作评论后端不可靠。

目标：迁移到 **Giscus**（GitHub Discussions 作评论后端）。零后端成本、评论即 GitHub Discussion（可用 GitHub 生态管理）、与 GitHub Pages 部署天然契合、不存在被第三方归档的风险。

**旧评论放弃**：Giscus 无 Valine 数据迁移通道；LeanCloud 应用处于归档态，恢复与导出成本高于评论本身价值（评论量小）。归档数据仍留在 LeanCloud 云端，未来如需仍可恢复导出。

## 范围

- **只改动** `_config.butterfly.yml` 的评论相关配置段（`comments.use`、`giscus:` 段、`valine:` 段）。
- **不做**：旧评论迁移、文章内容修改（含《基于Valine部署博客的评论系统》一文）、其他评论系统配置。
- **保持不变**：博客其余一切配置。

## 前置条件（用户操作，无法自动化）

Giscus 需要三个运行时参数，其中 repo_id 已通过免认证 API 获取（`R_kgDOMEsqYw`），其余需用户完成：

1. **启用 Discussions**：GitHub → 仓库 `chestnut19981123/chestnut19981123.github.io` → Settings → General → Features → 勾选 Discussions。当前未启用（`/discussions` 返回 404）。
2. **安装 giscus app**：https://github.com/apps/giscus → Install → 授权到该仓库（需要仓库拥有者操作）。
3. **获取 category_id**：访问 https://giscus.app/ → 输入仓库名 → 选择一个 Discussion 分类（如 Announcements / General）→ 把生成的 `data-category-id` 值发给实现者（或在配置中选择任意分类，参数由实现者填入）。

## 具体改动

`_config.butterfly.yml` 中：

### 1. 切换评论系统（第 422 行）

```yaml
use: Giscus
```

### 2. 填充 giscus 段（第 509-517 行）

```yaml
giscus:
  repo: chestnut19981123/chestnut19981123.github.io
  repo_id: R_kgDOMEsqYw
  category_id: <用户提供>
  theme:
    light: light
    dark: dark
  option:
```

### 3. 清理 valine 段（第 461-467 行）

删除 `appId` / `appKey` / `serverURLs` 三行（已失效的遗留凭据），段内其余键（`avatar`、`bg`、`visitor`、`option` 等）**原样保留不改动**（valine 段整体不再被加载，保留仅为配置参考）。

### 4. 最新评论组件

无需处理：主题内置逻辑 `card_newest_comment.pug:1` 将 Giscus 列入排除名单，切到 Giscus 后侧边栏「最新评论」组件自动隐藏（其数据源是 Valine API，若继续渲染只会报错）。

## 主题机制说明

- `themes/butterfly/layout/includes/third-party/comments/giscus.pug`：渲染 giscus client.js，使用 `data-repo` / `data-repo-id` / `data-category-id` / `data-mapping: pathname`（按页面路径关联讨论）/ `data-theme`（跟随站点明暗模式，`light`/`dark`）/ `data-reactions-enabled: '1'`，`option` 对象可覆盖任意 data-* 属性。
- 评论与文章按 pathname 关联：同一篇文章页面对应同一个 Discussion，跨设备/跨部署地址（localhost 与线上路径一致时）可共用。

## 决策记录

| 决策 | 理由 |
|------|------|
| Giscus vs 恢复 Valine | LeanCloud 免费版会再次归档，恢复不可持续；Giscus 零后端、与 GitHub Pages 同生态、评论可被 GitHub 社区检索 |
| 放弃旧评论 | 无迁移通道；归档态恢复成本高；评论量小，价值低于成本 |
| 删除 valine 凭据 | 已失效的遗留密钥，保留无意义 |
| 方案 A：实现者改配置，用户只做 GitHub 侧操作 | 用户无需接触 YAML 语法；参数通过 giscus.app 官方配置器获取，不易出错 |
| 主题 light/dark 跟随站点模式 | Giscus 官方支持，无需自定义 |

## 验证方式

1. 前置条件完成后，实现者填入 `category_id`，`npm run build` 确认构建通过。
2. `npm run server` 本地启动，打开任一文章页：
   - 评论区显示 Giscus 评论框（GitHub 登录后可发表评论）
   - 侧边栏「最新评论」组件不再显示
   - 明暗模式切换时评论区主题跟随
   - 浏览器控制台无报错
3. 确认无误后合并到 `main`，GitHub Actions 自动构建部署；线上再确认一次评论区加载。

## 回滚方案

改动仅涉及 `_config.butterfly.yml` 一个文件的三个配置段。回滚：恢复 `comments.use: Valine`、清空 giscus 段、恢复 valine 凭据（凭据已从 git 历史可恢复），推送后即回到 Valine（其 LeanCloud 应用仍处于归档态，需先恢复应用才可用）。
