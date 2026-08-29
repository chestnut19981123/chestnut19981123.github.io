# Repository Guidelines

This repository hosts a personal blog ("一粟") built with Hexo 8 and the Butterfly theme, deployed to GitHub Pages. Content is written in Chinese. The site uses KaTeX for math rendering and Giscus for comments.

## Project Structure & Module Organization

- `source/_posts/` — posts, organized by category: `AI/`, `技术/` (technical), `数学/` (mathematics), `算法/` (algorithms)
- `source/` — other content pages (`about/`, `tags/`, `categories/`) and shared assets under `source/img/`
- `scaffolds/` — templates for `hexo new` (post, page, draft)
- `themes/butterfly/` — Butterfly theme, managed as a **git submodule** (do not edit theme internals directly; update the submodule instead)
- `_config.yml` — Hexo site configuration
- `_config.butterfly.yml` — Butterfly theme overrides (navigation, comments, math, widgets, etc.)
- `.github/workflows/pages.yml` — CI/CD pipeline that auto-builds and deploys on push to `main`
- `.github/dependabot.yml` — daily npm dependency updates

## Build, Test, and Development Commands

```bash
npm install          # install dependencies (run after adding packages)
npm run server       # start local dev server with live reload (http://localhost:4000)
npm run build        # generate the static site into public/
npm run clean        # remove generated files (public/, db.json)
npm run deploy       # deploy the generated site to GitHub Pages
```

**Deployment flow**: On push to `main`, GitHub Actions (`pages.yml`) checks out the repo with submodules, installs Node.js 20, caches `node_modules`, builds the site, and deploys the `public/` directory to GitHub Pages. No manual `npm run deploy` is needed for normal releases.

## Coding Style & Naming Conventions

- Indent with two spaces for YAML and Stylus; follow Hexo defaults for templates.
- Use lowercase-with-hyphens for files and directories; keep post filenames aligned with their titles.
- Write post content in Markdown with YAML front matter. Required fields: `title`, `date`, `categories`, `tags`, `cover`.
- Use `hexo new post "Title"` to create posts from the scaffold template (`scaffolds/post.md`).
- Enable `post_asset_folder: true` in `_config.yml` — each post gets its own asset directory for images and diagrams.
- No linter or formatter is configured; keep edits minimal and consistent with surrounding files.

## Testing

There is no automated test suite. Verify changes by:

- Running `npm run server` and reviewing new or edited pages in a browser.
- Running `npm run build` and confirming the site generates without errors.
- Checking image paths, KaTeX math rendering, and front matter fields in rendered output.

## Theme & Configuration

- **Theme**: Butterfly (`hexo-theme-butterfly`) via git submodule pinned to `main` branch.
- **Two config files**: `_config.yml` controls Hexo core (site metadata, URL, permalinks, Markdown plugins). `_config.butterfly.yml` controls theme features (menus, widgets, comments, math, dark mode, etc.).
- **Comment system**: Giscus, configured with repo `chestnut19981123/chestnut19981123.github.io`. The `category_id` is stored in `_config.butterfly.yml` under `giscus`.
- **Math rendering**: KaTeX via `@renbaoshuo/markdown-it-katex` plugin (Hexo 8 uses markdown-it renderer). KaTeX is loaded per-page; add `katex: true` to front matter when a post uses math.
- **Post asset folders**: Set `post_asset_folder: true` in `_config.yml`. Each post gets a directory under `source/_posts/` for its images, SVGs, and other assets.

## Commit & Pull Request Guidelines

- Commit subjects in Chinese. Use conventional prefixes (`feat:`, `fix:`, `refactor:`) followed by a short description, e.g., `feat: 新增矩阵求导速查手册` or `refactor: 分类统一归入技术`. Plain descriptive subjects are also acceptable.
- Pull requests should describe the change, note related posts or issues, and mention whether assets (images, SVG figures) were added or modified.
- Keep content-only changes separate from configuration or theme changes.

## Security

- **Secrets in config**: The Giscus `repo_id` and `category_id` are present in `_config.butterfly.yml` (lines 508-509). These are public identifiers tied to the GitHub Discussions integration and are not considered sensitive, but do not add additional API keys or tokens to config files committed to the repo.
- **Removed credentials**: The Valine `appId` was previously exposed in the config but has been removed (archived LeanCloud app). Do not reintroduce secrets into version-controlled config files.
- **Dependabot**: Enabled for daily npm updates with a limit of 20 open PRs. Review dependabot PRs promptly for security patches.
- **Generated files**: `public/`, `db.json`, `.deploy*/`, and `docs/superpowers/` are gitignored. Do not commit build artifacts.

## License

Post content is licensed under CC BY-NC-SA 4.0 (configured in `post_copyright` section of `_config.butterfly.yml`).

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