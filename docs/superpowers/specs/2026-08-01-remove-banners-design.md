# 移除页面横幅图 — 设计文档

日期：2026-08-01
状态：已批准

## 背景与目标

博客（Hexo + Butterfly 主题）的首页、归档、标签、分类、关于等页面顶部各有一张大尺寸照片横幅（`top_img.jpg`、`archive_img.jpg`、`tag_img.jpg`、`category_img.jpg`、`about_img.jpg`），文章页还会把封面图当横幅。照片横幅与博客「一粟」简洁克制的基调不协调。

目标：**完全去掉所有页面的顶部横幅**，内容直接以干净背景呈现；文章卡片封面保留（首页/归档列表仍显示封面图）。纯使用 Butterfly 主题内置能力（`top_img: false` / 配置项设 `false`），不引入自定义代码。

## 范围

- 改动 `_config.butterfly.yml`、3 个静态页面前注、7 篇文章前注；删除 5 张共享横幅图片。
- **保持不变**：博客名称、主题色、文章封面（`cover` 字段及图片）、背景特效、导航栏、footer 等一切其他配置。

## 具体改动

### 1. 配置：四个横幅图关闭（`_config.butterfly.yml`）

```yaml
# 首页
index_img: false
# 归档页
archive_img: false
# 子标签页
tag_img: false
# 子分类页
category_img: false
```

### 2. 静态页面前注：`top_img: false`

- `source/tags/index.md`（原 `top_img: '/img/tag_img.jpg'`）
- `source/categories/index.md`（原 `top_img: '/img/category_img.jpg'`）
- `source/about/index.md`（原 `top_img: '/img/about_img.jpg'`）

> 注意：必须显式写 `false` 而不是删掉该行——删掉会回落到 `theme.default_top_img`（当前为空），标题仍会以横幅形式渲染在页面中部；显式 `false` 才会跳过整个横幅块。

### 3. 7 篇文章 front matter：新增 `top_img: false`

`source/_posts/` 下全部 7 篇（技术 4 篇、数学 2 篇、算法 1 篇）。文章页横幅取 `page.top_img || page.cover`，设 `false` 后不再把封面当横幅；`cover` 字段保留，列表卡片封面不受影响。

### 4. 删除图片文件（`source/img/`）

- `top_img.jpg`、`archive_img.jpg`、`tag_img.jpg`、`category_img.jpg`、`about_img.jpg`

已确认这 5 张图仅被上述配置/前注引用，无其他引用点，可安全删除。

## 主题机制说明

Butterfly 横幅渲染逻辑（`themes/butterfly/layout/includes/header/index.pug`）：

- 页面级：`page.top_img !== false` 才渲染横幅块；`top_img: false` 时 `isHomeClass = 'not-top-img'`，仅剩导航栏。
- 页面类型级：`theme.index_img !== false` / `archive_img` / `tag_img` / `category_img` 同理，设 `false` 即关闭。
- 无横幅时页面标题降级为正文内标题（`page.pug` 的 `h1.page-title`、`post.pug` 引入正文中的 post-info），不会出现标题丢失或与导航栏重叠。

## 决策记录

| 决策 | 理由 |
|------|------|
| 方案 A：局部设 `false` + 删图 | 与全局开关（方案 C）效果相同，但保留单页面/单文章恢复横幅的能力；不保留无用图片（方案 B 会留 1.4MB 冗余） |
| 显式 `top_img: false` 而非删除字段 | 删除字段会回落到 default_top_img 分支，横幅块仍渲染 |
| 文章页横幅一并去掉 | 阅读界面更干净，符合「纯粹」目标；卡片封面与文章横幅解耦，封面仍保留 |
| 关于页横幅一并去掉 | 与用户确认，保持全站统一 |

## 验证方式

1. `npm run server` 本地启动，逐页检查：
   - 首页、归档、标签、分类、关于：顶部无横幅图，标题正常显示，导航栏正常
   - 任一文章页（如 /2024/06/14/0a8c93d/）：顶部无封面横幅，正文标题正常
   - 首页/归档的文章卡片：封面图仍显示
2. 图片目录确认 5 张图已删除且页面无 404 报错（浏览器控制台检查）
3. 确认无误后 push 到 `main`，GitHub Actions 自动构建并部署

## 回滚方案

改动涉及 1 个配置文件、10 个 md 文件的 front matter、5 张图。回滚方式：恢复 `_config.butterfly.yml` 四个配置项为原图片路径，删除各 md 中的 `top_img: false`，用 `git` 恢复 5 张图片文件即可。
