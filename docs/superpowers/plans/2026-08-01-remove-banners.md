# 移除站级页面横幅图 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 去掉首页、归档、标签、分类、关于五个站级页面的顶部照片横幅并删除 5 张共享横幅图片，文章页横幅（封面图）保持不变。

**Architecture:** 纯声明式改动，不写任何代码：`_config.butterfly.yml` 四个配置键设 `false`、三个静态页面前注设 `top_img: false`（显式 `false` 而非删除——删除会回落到 `default_top_img` 分支导致横幅块仍渲染）、删除 5 张图片文件。验证靠构建产物 grep 检查 + 本地浏览器逐页人工确认。

**Tech Stack:** Hexo 7.3 / Node 20、Butterfly 主题（submodule）、YAML 配置、Markdown front matter。无测试框架——验证方式是 `hexo generate` 产物检查。

## Global Constraints

- 纯使用 Butterfly 主题内置能力（`top_img: false` / 配置项设 `false`），不引入任何自定义代码或 CSS。
- 文章 front matter 零改动；`cover` 字段及封面图片全部保留（文章页横幅与列表卡片封面都依赖它）。
- 显式写 `top_img: false`，禁止删除 front matter 中的 `top_img` 行（原因见上）。
- 关于页没有 `about_img` 配置键，其横幅只能靠前注关闭。
- 不在本次范围：背景特效、导航栏、主题色、footer、文章内容。
- 每完成一个任务即提交一次；提交信息用中文，符合仓库现有风格。

---

### Task 1: 关闭 `_config.butterfly.yml` 中的四个横幅配置

**Files:**
- Modify: `_config.butterfly.yml:59`（`index_img`）
- Modify: `_config.butterfly.yml:65`（`archive_img`）
- Modify: `_config.butterfly.yml:69`（`tag_img`）
- Modify: `_config.butterfly.yml:78`（`category_img`）

**Interfaces:**
- Consumes: 无（首个任务）
- Produces: 四个配置键设为 `false` 的 `_config.butterfly.yml`——后续任务不依赖此配置的具体值，但 Task 4 的构建验证会检查其结果

- [ ] **Step 1: 修改 `index_img`**

用 Edit 工具，`old_string: "index_img: /img/top_img.jpg"`，`new_string: "index_img: false"`（该行是文件中唯一含 `index_img: /img/top_img.jpg` 的行）。

- [ ] **Step 2: 修改 `archive_img`**

用 Edit 工具，`old_string: "archive_img: /img/archive_img.jpg"`，`new_string: "archive_img: false"`。

- [ ] **Step 3: 修改 `tag_img`**

用 Edit 工具，`old_string: "tag_img: /img/tag_img.jpg"`，`new_string: "tag_img: false"`。

- [ ] **Step 4: 修改 `category_img`**

用 Edit 工具，`old_string: "category_img: /img/category_img.jpg"`，`new_string: "category_img: false"`。

- [ ] **Step 5: 验证四个键的值**

Run: `grep -nE "^(index_img|archive_img|tag_img|category_img):" _config.butterfly.yml`
Expected: 四行均以 `: false` 结尾，无其他键被误改。

- [ ] **Step 6: 提交**

```bash
git add _config.butterfly.yml
git commit -m "移除站级页面横幅：关闭首页/归档/标签/分类横幅配置

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: 三个静态页面前注改为 `top_img: false`

**Files:**
- Modify: `source/tags/index.md`（front matter 第 5 行）
- Modify: `source/categories/index.md`（front matter 第 5 行）
- Modify: `source/about/index.md`（front matter 第 4 行）

**Interfaces:**
- Consumes: 无（与 Task 1 相互独立）
- Produces: 三个页面 `page.top_img === false`——Task 4 构建后检查 `not-top-img` 类时依赖

- [ ] **Step 1: 修改 `source/tags/index.md`**

用 Edit 工具，`old_string: "top_img: '/img/tag_img.jpg'"`，`new_string: "top_img: false"`。

- [ ] **Step 2: 修改 `source/categories/index.md`**

用 Edit 工具，`old_string: "top_img: '/img/category_img.jpg'"`，`new_string: "top_img: false"`。

- [ ] **Step 3: 修改 `source/about/index.md`**

用 Edit 工具，`old_string: "top_img: '/img/about_img.jpg'"`，`new_string: "top_img: false"`。

- [ ] **Step 4: 验证 source 下不再引用这 5 张图**

Run: `grep -rn "top_img.jpg\|archive_img.jpg\|tag_img.jpg\|category_img.jpg\|about_img.jpg" _config.yml _config.butterfly.yml source/ --include="*.md" --include="*.yml" --include="*.yaml"`
Expected: 无任何输出（三处前注已改、Task 1 已把配置改成 false；若仍有输出说明有遗漏，检查后修正）。

- [ ] **Step 5: 提交**

```bash
git add source/tags/index.md source/categories/index.md source/about/index.md
git commit -m "移除站级页面横幅：标签/分类/关于页面前注 top_img 设为 false

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 删除 5 张共享横幅图片

**Files:**
- Delete: `source/img/top_img.jpg`
- Delete: `source/img/archive_img.jpg`
- Delete: `source/img/tag_img.jpg`
- Delete: `source/img/category_img.jpg`
- Delete: `source/img/about_img.jpg`

**Interfaces:**
- Consumes: Task 2 完成后 source 内已无对这 5 个文件名的引用
- Produces: 干净的 `source/img/`——Task 4 构建产物中不应再出现这 5 个文件名

- [ ] **Step 1: 删除 5 张图片**

Run: `git rm source/img/top_img.jpg source/img/archive_img.jpg source/img/tag_img.jpg source/img/category_img.jpg source/img/about_img.jpg`
Expected: 5 个 `rm 'source/img/xxx.jpg'` 输出，无报错。

- [ ] **Step 2: 全仓库（排除构建产物与主题）确认无残留引用**

Run: `grep -rn --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=public --exclude-dir=themes "top_img.jpg\|archive_img.jpg\|tag_img.jpg\|category_img.jpg\|about_img.jpg" .`
Expected: 仅命中 `docs/superpowers/specs/2026-08-01-remove-banners-design.md` 与 `docs/superpowers/plans/2026-08-01-remove-banners.md` 两处（计划文档对变更对象本身的描述性提及，属预期内）；`_config*.yml` 与 `source/` 内必须零命中。

- [ ] **Step 3: 确认其余图片不受影响**

Run: `ls source/img/ | wc -l`
Expected: 14（原 19 个文件 − 5 个删除；`avatar.jpg`、`cover1~10.jpg`、`alipay.png`、`wechat.png` 等仍在）。

- [ ] **Step 4: 提交**

```bash
git commit -m "移除站级页面横幅：删除 5 张共享横幅图片

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: 构建验证 + 人工逐页检查

**Files:**
- 无新增/修改（只读验证；若验证发现问题，回到对应任务修复）

**Interfaces:**
- Consumes: Task 1–3 的全部产物
- Produces: 验证通过的结论 + 待用户合并的最终 diff

- [ ] **Step 1: 生成静态站点**

Run: `npm run build`
Expected: `hexo generate` 完成，无报错。

- [ ] **Step 2: 构建产物中无 5 张图片引用**

Run: `grep -rn "top_img.jpg\|archive_img.jpg\|tag_img.jpg\|category_img.jpg\|about_img.jpg" public/`
Expected: 无任何输出（若有输出说明有遗漏的引用点，回到 Task 2/3 排查）。

- [ ] **Step 3: 5 个站级页面均带 `not-top-img` 类**

Run: `grep -l "not-top-img" public/index.html public/archives/index.html public/tags/index.html public/categories/index.html public/about/index.html`
Expected: 5 个文件全部列出（说明横幅块被跳过，仅剩导航栏）。

- [ ] **Step 4: 文章页保留横幅（封面仍作 banner）**

Run: `grep -rl "post-bg" public --include=index.html`
Expected: 输出 7 个文章页路径（形如 `public/2024/../<hash>/index.html`），每页 `#page-header` 带 `post-bg` 类（即横幅仍在渲染）。再运行 `grep -rl "cover\.\(jpg\|png\)" public --include=index.html | sort`，Expected: 8 个文件（public/index.html、public/archives/index.html + 6 个有封面的文章页：hello-world、求导积分速查表、三棱锥外接球半径公式、基于Valine部署博客的评论系统、Spring基础、Linux配置网络），即封面引用仍在。

- [ ] **Step 5: 本地启动并人工逐页确认**

Run: `npm run server`，然后访问 http://localhost:4000，逐项确认：
- 首页、归档（/archives/）、标签（/tags/）、分类（/categories/）、关于（/about/）：顶部无横幅图，页面标题正常显示，导航栏正常
- 从首页点开任意文章：顶部仍是该文章的封面横幅，正文标题正常
- 首页与归档的文章卡片：封面图仍显示
- 浏览器控制台无图片 404 报错

- [ ] **Step 6: 汇总结果**

向用户展示 `git log --oneline -3` 与 `git status`，说明改动范围；由用户决定合并分支 / push 到 `main`（CI 会自动构建部署）。此步不做任何提交（无新改动）。
