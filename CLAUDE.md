# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概览

个人博客「一粟」，基于 Hexo 8.1.2 + Butterfly 主题（git 子模块，固定在 4.13 版本），部署在 GitHub Pages。内容以中文撰写（`language: zh-CN`，时区 `Asia/Shanghai`），主要包含数学（向量微积分）、技术（Spring、Linux）、算法三类文章。

## 常用命令

```bash
npm run server   # 本地预览，默认 http://localhost:4000
npm run build    # hexo generate，生成静态站点到 public/
npm run clean    # hexo clean，清除缓存与 db.json
```

没有测试和 lint 脚本。`db.json`、`public/`、`node_modules/` 均被 gitignore，不要手动编辑 `db.json`（`npm run clean` 可重建）。

## 部署流程

推送到 `main` 分支即触发 `.github/workflows/pages.yml`：
1. checkout（`submodules: recursive`，拉取主题子模块）
2. `npm install` → `npm run build`
3. 上传 `public/` 并用 actions/deploy-pages 发布

`_config.yml` 中 `deploy` 配置为空——部署完全走 GitHub Actions，不要用 `hexo deploy`。

## 内容结构

- `source/_posts/` 按分类建目录：`技术/`、`数学/`、`算法/`，每篇文章一个 `.md` + 同名资源文件夹（`post_asset_folder: true` 已开启），图片用相对文件名引用，如 `![描述](cover.jpg)`、`![描述](fig-line1.png)`。
- Front matter 惯例：`categories: '数学'`（单分类用字符串）、`tags: [...]`、`date`、`cover: cover.jpg`；数学文章必须加 `katex: true`。
- 数学文章中的示意图（`fig-*.png`）是用 matplotlib 生成的 3D 投影图，迭代时通过 git 历史与 `docs/superpowers/specs/` 中的设计文档对齐视觉规范（微元箭头指向、面片朝向、标题风格等）。
- `source/about/`、`source/categories/`、`source/tags/`、`source/gallery/` 为各页面入口（含 front matter 设置 `top_img: false` 等）。
- 新增文章模板见 `scaffolds/post.md`。

## 数学公式渲染（KaTeX）——易错点

- 构建端：`_config.yml` 中 `markdown.plugins` 用 `@renbaoshuo/markdown-it-katex`（依赖 `katex` ^0.18.1）在构建时渲染公式。
- 前端：`_config.butterfly.yml` 的 `inject.head` 中通过 CDN 加载 `katex.min.css`（当前固定 0.18.1）。
- **两个版本必须保持一致**：katex 0.18 起类名从 `base`/`strut` 改为 `katex-base`/`katex-strut`，若 CDN 仍是 0.16.9，`.base`/`.strut` 规则失效会导致公式布局异常（曾因此回滚过版本）。

## 主题配置

- `themes/butterfly/` 是 git 子模块（jerryc127/hexo-theme-butterfly，分支 main），未做本地修改——不要直接改子模块内文件，不要提交子模块内部的改动。
- 主题的全部定制都在仓库根目录的 `_config.butterfly.yml`（Hexo 会将根目录 `_config.<theme>.yml` 与主题内配置合并，根目录版本优先）。
- 评论系统用 Giscus（`giscus.repo: chestnut19981123/chestnut19981123.github.io`，`data-mapping: title`）。
- 站点级 URL、社交链接、giscus 仓库等标识都跟随 GitHub 用户名 `chestnut19981123`（改用户名时需同步更新 `_config.yml`、`_config.butterfly.yml`）。

## 设计文档

`docs/superpowers/plans/` 与 `docs/superpowers/specs/` 存放过往功能/文章的设计文档（背景效果、去横幅、Giscus 评论、场积分文章等），涉及较大改动前可先查阅以保持思路一致。
