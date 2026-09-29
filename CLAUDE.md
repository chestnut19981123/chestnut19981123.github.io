# 仓库指南

个人博客「一粟」，基于 Hexo 8.1.2 + Butterfly 主题（git 子模块，固定在 4.13 版本），部署到 GitHub Pages。内容使用中文（`language: zh-CN`，时区 `Asia/Shanghai`），按 `AI/`、`技术/`、`数学/`、`算法/` 分类（如数学以向量微积分为主，技术涉及 Spring、Linux）。没有测试套件，也没有 linter——用 `npm run build` 和 `npm run server`（http://localhost:4000）验证。

## 项目结构

- `source/_posts/` —— 按分类组织文章：`AI/`、`技术/`、`数学/`、`算法/`。每篇文章是一个 `.md` 文件，配有同名资源文件夹（`post_asset_folder: true`）；图片用相对文件名引用（`![描述](cover.png)`）。
- `source/` —— 页面（`about/`、`categories/`、`tags/`、`gallery/`，front matter 含 `top_img: false` 等设置）和 `source/img/` 下的共享资源。
- `scaffolds/` —— `hexo new` 使用的模板（`post.md` 只含最简 front matter：`title`、`categories`、`tags`、`date`）。
- `scripts/pangu-render.js` —— 构建期的 pangu（在 CJK 与拉丁字符之间加空格），注册为 `after_render:html`。它会跳过 `script/style/pre/code/kbd/samp/.katex/math/svg`。Butterfly 自带的 `pangu` 配置自主题 5.3.0 起已失效；npm 的 `pangu` 依赖只供这个脚本使用。
- `themes/butterfly/` —— Butterfly 主题以 **git submodule** 形式引入（jerryc127/hexo-theme-butterfly，分支 `main`，固定在 4.13）。不要改主题内部；通过根目录的 `_config.butterfly.yml` 定制（根配置优先于主题默认值）。
- `_config.yml` —— Hexo 核心配置（站点、permalink `:hash/`、`post_asset_folder: true`、`updated_option: 'mtime'`、markdown-it + KaTeX 插件）。`_config.butterfly.yml` —— 主题功能（giscus、数学、封面、注入等）。
- `docs/superpowers/{plans,specs,figs}/` —— 过去功能/文章的本地设计文档（已 gitignore）。大改动前先查阅，保持思路一致。

## 常用命令

```bash
npm run server   # 本地开发服务器，带热重载（http://localhost:4000）
npm run build    # hexo generate → 静态站点输出到 public/
npm run clean    # hexo clean → 删除 public/、db.json（不要手工编辑 db.json）
```

没有测试和 lint 脚本。`db.json`、`public/`、`node_modules/` 均被 gitignore，不要手动编辑 `db.json`（`npm run clean` 可重建）。

## 部署流程

- **部署只走 GitHub Actions。** `_config.yml` 的 `deploy` 配置为空，所以 `npm run deploy` / `hexo deploy` 什么都不做。推送到 `main` 会触发 `.github/workflows/pages.yml`：
  1. checkout（`submodules: recursive`，拉取主题子模块；`fetch-depth: 0`）
  2. `npm install` → `npm run build`（Node 20）
  3. 部署 `public/`
- CI 在构建前会从 git 历史恢复每篇文章的 mtime（`git log -1 --format=%cI` + `touch`）。否则 `updated_option: 'mtime'` 会把所有文章的「更新于」日期塌缩成构建时间。

## 内容约定

- front matter：`title`、`date`、`categories`（单个分类写成字符串，如 `'数学'`）、`tags: [...]`、`cover: cover.jpg`/`.png`。**数学文章必须加 `katex: true`**（`math.per_page: false` —— KaTeX 按页加载）。
- 用 `hexo new post "标题"` 创建文章；文件名用 lowercase-with-hyphens，与标题对应。
- 数学文章的示意图（`fig-*.png`）是用 matplotlib 生成的 3D 投影图；迭代时对照 git 历史与 `docs/superpowers/specs/` 中的设计文档，保持视觉规范（微元箭头指向、面片朝向、标题风格等）。

## KaTeX —— 两个版本保持同步

构建侧的 `@renbaoshuo/markdown-it-katex`（依赖 `katex` ^0.18.1）在构建时渲染公式；前端通过 `_config.butterfly.yml` 的 `inject.head` 用 CDN 加载 `katex.min.css`（当前固定 0.18.1）。两边必须都停留在 katex 0.18.x：0.18 把 `base` / `strut` 类改名为 `katex-base` / `katex-strut`，如果 CDN 还停留在 0.16.9，`.base`/`.strut` 规则失效会导致公式布局异常（本站为此回滚过一次）。

## 主题配置

- `themes/butterfly/` 是 git 子模块，未做本地修改——不要直接改子模块内的文件，也不要提交子模块内部的改动。
- 主题的全部定制都在仓库根目录的 `_config.butterfly.yml`（Hexo 会将根目录 `_config.<theme>.yml` 与主题内配置合并，根目录版本优先）。
- 评论系统用 Giscus（`giscus.repo: chestnut19981123/chestnut19981123.github.io`，`data-mapping: title`）。
- 站点级 URL、社交链接、giscus 仓库等标识都跟随 GitHub 用户名 `chestnut19981123`（改用户名时需同步更新 `_config.yml`、`_config.butterfly.yml`）。

## 提交指南

- commit 主题用中文，带约定前缀（`feat:`、`fix:`、`refactor:`）或纯描述性主题。
- 纯内容改动与配置/主题改动分开提交。
- 提交前必须运行 `pre-commit`（见全局规则）；禁止使用 `--no-verify`。

## 安全与忽略文件

- `_config.butterfly.yml` 里的 Giscus `repo_id` / `category_id` 是公开标识符，关联 GitHub Discussions——不敏感。不要把真实的 API key / token 加进要提交的配置（Valine 的 `appId` 曾暴露过一次，后来已移除）。
- Dependabot 每天跑 npm 更新（20 个 PR 上限）；及时审查。
- 已 gitignore：`node_modules/`、`public/`、`db.json`、`.deploy*/`、`docs/superpowers/`、`.superpowers/`。绝不提交构建产物。

## 许可证

文章内容采用 CC BY-NC-SA 4.0（`_config.butterfly.yml` 中的 `post_copyright`）。

---

# 迁移的 Claude 记忆

## 用户配图审美与迭代方式

用户对博客配图的审美偏好：对称布局（等宽列、严格镜像）、圆润线条（贝塞尔曲线、大曲率半径）、干净矢量风（拒绝 AI 生成的乱码图）、配色语言统一（蓝 = LLM、橙 = 权限门、绿 = 执行工具、红 = 拒绝/危险，灰 `#64748b` 为中性线条）。

注意区分「品味」与「情境决策」：**浅色底不是品味**。封面用浅色是那次为与全站其他封面保持一致而做的情境决定，不代表用户偏好浅色；下次做新封面把深浅当作开放选项，不要默认浅色。

提需求时用精确的几何语言（「方块对称一点」「线条圆润点」「箭头左右对称」「箭头 120 度」），每处改动都要求可计算、可像素验证。迭代节奏：一次一张图，改完验证后小步提交（格式 `Agent实现原理深度版：<摘要>`），推送触发 CI 部署。

**如何应用：** 改图前先核对对称性/圆角/配色一致性；模糊需求（如「120 度」）先翻译成几何约束（镜像对满足 800-x、角度相对水平 60°）再动手并在回复中陈述解读；改完像素验证后再提交。

## Butterfly 封面横幅行为

Butterfly 4.13 文章页横幅（`header.post-bg`）对封面的确定性行为，设计封面时必须按此规划：

- 横幅 1280×400，`background-size: cover` + `position: 50% 50%` → 只显示 1280×720 封面的**中心带（封面 y 160-560）**，上下各裁 160px。
- 横幅叠 `::before rgba(0,0,0,0.3)` 暗色遮罩；白色 35px 标题固定落在横幅 y 256-309 = **封面 y 416-469** —— 该带必须干净（浅色封面标题对比度约 2.2:1 为全站常态，白字压浅色实体框会被吞）。
- 懒加载：文章内 img 用 `data-lazy-src`（src 初始为 1px GIF + `filter: blur(8px)`）。验证须 scrollIntoView 触发，轮询到 `filter` 为 none/blur(0) 再截图；CSS 属性选择器要用 `img[data-lazy-src*=...]` 而非 `img[src*=...]`，且片段要够精确（多匹配会触发 Playwright 严格模式）。
- 首页卡片/侧栏缩略图共用同一封面（59×59 缩放渲染），细线在缩略尺寸下变亚像素属正常。

**如何应用：** 画新封面先算标题带（y 416-469）与可见窗口（y 160-560），实体元素避开标题带；验证走 Playwright + `data-lazy-src` 定位 + blur 轮询。

## SVG fig 验收管线

本仓库 fig-*.svg 的 marker 坑与验收方法（Read 工具在本环境无法显示图片，视觉验证全靠像素分析）：

- **markerUnits 默认 strokeWidth** → 箭头渲染尺寸 = markerWidth × stroke-width（9 × 2.5 = 22.5px）。线段长度必须 ≥ 约 2.5 × 箭头渲染长，否则箭头吞线。
- `refX` 语义（viewBox 0-10）：refX=10 箭头尖精确落在线段末端；refX=8 会伸出 4.5px。仓库现状两套并存：fig-vs/fig-loop 用 8，fig-permission/cover 用 10。
- 所有 fig 的 marker fill 统一为 `#64748b` 灰（即便线条是彩色）——灰色箭头头是设计而非 bug。
- 验收管线：几何计算（直线方程采样、贝塞尔曲率半径采样、镜像 800-x 关系）→ Playwright 元素截图 → PIL 精确坐标像素探针 + ±2px 邻域确认。
- 亚像素采样点会落在 AA 边缘得到混合色（如 112,127,148）——用 ±2px 邻域扫描确认，勿因单像素报假阳性。ASCII 粗采样会误读（行/列映射错、浅色填充被分类成流浪线条）——回到精确坐标逐点探测。
- 设计值取整会破坏数学检查（118×tan(30°)=68.127 vs 取整 68.1 → 0.03px 镜像「偏差」）——先以数学精确值为准再验证。

**如何应用：** 画新 fig 先验算 marker 尺寸与线长比；改线位后按线方程采样验证；提交前跑完整像素验证。
