# Repository Guidelines

Personal blog ("一粟") built with Hexo 8.1.2 + Butterfly theme, deployed to GitHub Pages. Content is written in Chinese (`language: zh-CN`, timezone `Asia/Shanghai`). No test suite and no linter — verify via `npm run build` and `npm run server` (http://localhost:4000).

## Project Structure

- `source/_posts/` — posts organized by category: `AI/`, `技术/`, `数学/`, `算法/`. Each post is a `.md` file with a same-named asset folder (`post_asset_folder: true`); reference images by relative filename (`![描述](cover.png)`).
- `source/` — pages (`about/`, `categories/`, `tags/`, `gallery/`) and shared assets under `source/img/`.
- `scaffolds/` — templates for `hexo new` (`post.md` has minimal front matter: `title`, `categories`, `tags`, `date`).
- `scripts/pangu-render.js` — build-time pangu (spaces between CJK and Latin) registered as `after_render:html`. It skips `script/style/pre/code/kbd/samp/.katex/math/svg`. Butterfly's own `pangu` config is dead since theme 5.3.0; the npm `pangu` dependency feeds only this script.
- `themes/butterfly/` — Butterfly theme as a **git submodule** (jerryc127/hexo-theme-butterfly, branch `main`). Do not edit theme internals; customize via root `_config.butterfly.yml` (root config wins over theme defaults).
- `_config.yml` — Hexo core (site, permalink `:hash/`, `post_asset_folder: true`, `updated_option: 'mtime'`, markdown-it + KaTeX plugin). `_config.butterfly.yml` — theme features (giscus, math, cover, inject, etc.).
- `docs/superpowers/{plans,specs,figs}/` — local design docs for past features/posts (gitignored). Consult before large changes.

## Build & Deploy

```bash
npm run server   # local dev server with live reload (http://localhost:4000)
npm run build    # hexo generate → static site into public/
npm run clean    # hexo clean → removes public/, db.json (don't edit db.json by hand)
```

- **Deployment is GitHub Actions only.** `_config.yml` has empty `deploy` config, so `npm run deploy`/`hexo deploy` does nothing. Push to `main` triggers `.github/workflows/pages.yml` (checkout with `submodules: recursive` and `fetch-depth: 0`, Node 20, `npm install` → `npm run build`, deploy `public/`).
- The CI restores each post's mtime from git history (`git log -1 --format=%cI` + `touch`) before building. Without this, `updated_option: 'mtime'` would collapse every post's "更新于" (updated) date to build time.

## Content Conventions

- Front matter: `title`, `date`, `categories` (single category as string, e.g. `'数学'`), `tags: [...]`, `cover: cover.jpg`/`.png`. **Math posts must add `katex: true`** (`math.per_page: false` — KaTeX loads per-page).
- Create posts with `hexo new post "Title"`; filenames lowercase-with-hyphens, aligned with titles.

## KaTeX — keep the two versions in sync

Build-side `@renbaoshuo/markdown-it-katex` renders formulas at build time; front-end loads `katex@0.18.1` CSS/JS via CDN under `inject`/`CDN.option` in `_config.butterfly.yml`. Both must stay on katex 0.18.x: 0.18 renamed classes `base`/`strut` to `katex-base`/`katex-strut`, so a stale 0.16.9 CDN breaks formula layout (site was rolled back for exactly this once).

## Commit Guidelines

- Chinese commit subjects with conventional prefixes (`feat:`, `fix:`, `refactor:`) or plain descriptive subjects.
- Keep content-only changes separate from config/theme changes.
- `pre-commit` must run before committing (see global instructions); never use `--no-verify`.

## Security & Ignored Files

- Giscus `repo_id`/`category_id` in `_config.butterfly.yml` are public identifiers tied to GitHub Discussions — not sensitive. Do not add real API keys/tokens to committed config (a Valine `appId` was once exposed and later removed).
- Dependabot runs daily npm updates (20 PR limit); review promptly.
- Gitignored: `public/`, `db.json`, `.deploy*/`, `docs/superpowers/`, `.superpowers/`. Never commit build artifacts.

## License

Post content is CC BY-NC-SA 4.0 (`post_copyright` in `_config.butterfly.yml`).

---

# Migrated Claude Memory

## 用户配图审美与迭代方式

用户对博客配图的审美偏好：对称布局（等宽列、严格镜像）、圆润线条（贝塞尔曲线、大曲率半径）、干净矢量风（拒绝 AI 生成的乱码图）、配色语言统一（蓝=LLM、橙=权限门、绿=执行工具、红=拒绝/危险，灰 #64748b 为中性线条）。

注意区分「品味」与「情境决策」：**浅色底不是品味**。封面用浅色是那次为与全站其他封面保持一致而做的情境决定，不代表用户偏好浅色；下次做新封面把深浅当作开放选项，不要默认浅色。

提需求时用精确的几何语言（「方块对称一点」「线条圆润点」「箭头左右对称」「箭头 120 度」），每处改动都要求可计算、可像素验证。迭代节奏：一次一张图，改完验证后小步提交（格式 `Agent实现原理深度版：<摘要>`），推送触发 CI 部署。

**How to apply:** 改图前先核对对称性/圆角/配色一致性；模糊需求（如「120 度」）先翻译成几何约束（镜像对满足 800-x、角度相对水平 60°）再动手并在回复中陈述解读；改完像素验证后再提交。

## Butterfly 封面横幅行为

Butterfly 4.13 文章页横幅（`header.post-bg`）对封面的确定性行为，设计封面时必须按此规划：

- 横幅 1280×400，`background-size: cover` + `position: 50% 50%` → 只显示 1280×720 封面的**中心带（封面 y 160-560）**，上下各裁 160px。
- 横幅叠 `::before rgba(0,0,0,0.3)` 暗色遮罩；白色 35px 标题固定落在横幅 y 256-309 = **封面 y 416-469** —— 该带必须干净（浅色封面标题对比度 ~2.2:1 为全站常态，白字压浅色实体框会被吞）。
- 懒加载：文章内 img 用 `data-lazy-src`（src 初始为 1px GIF + `filter: blur(8px)`）。验证须 scrollIntoView 触发，轮询到 `filter` 为 none/blur(0) 再截图；CSS 属性选择器要用 `img[data-lazy-src*=...]` 而非 `img[src*=...]`，且片段要够精确（多匹配会触发 Playwright 严格模式）。
- 首页卡片/侧栏缩略图共用同一封面（59×59 缩放渲染），细线在缩略尺寸下变亚像素属正常。

**How to apply:** 画新封面先算标题带（y 416-469）与可见窗口（y 160-560），实体元素避开标题带；验证走 Playwright + data-lazy-src 定位 + blur 轮询。

## SVG fig 验收管线

本仓库 fig-*.svg 的 marker 坑与验收方法（Read 工具在本环境无法显示图片，视觉验证全靠像素分析）：

- **markerUnits 默认 strokeWidth** → 箭头渲染尺寸 = markerWidth × stroke-width（9 × 2.5 = 22.5px）。线段长度必须 ≥ ~2.5× 箭头渲染长，否则箭头吞线。
- `refX` 语义（viewBox 0-10）：refX=10 箭头尖精确落在线段末端；refX=8 会伸出 4.5px。仓库现状两套并存：fig-vs/fig-loop 用 8，fig-permission/cover 用 10。
- 所有 fig 的 marker fill 统一 #64748b 灰（即便线条是彩色）——灰色箭头头是设计而非 bug。
- 验收管线：几何计算（直线方程采样、贝塞尔曲率半径采样、镜像 800-x 关系）→ Playwright 元素截图 → PIL 精确坐标像素探针 + ±2px 邻域确认。
- 亚像素采样点会落在 AA 边缘得到混合色（如 112,127,148）——用 ±2px 邻域扫描确认，勿因单像素报假阳性。ASCII 粗采样会误读（行/列映射错、浅色填充被分类成流浪线条）——回到精确坐标逐点探测。
- 设计值取整会破坏数学检查（118×tan(30°)=68.127 vs 取整 68.1 → 0.03px 镜像"偏差"）——先以数学精确值为准再验证。

**How to apply:** 画新 fig 先验算 marker 尺寸与线长比；改线位后按线方程采样验证；提交前跑完整像素验证。
