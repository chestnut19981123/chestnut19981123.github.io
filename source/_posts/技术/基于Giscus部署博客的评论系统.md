---
title: 基于 Giscus 部署博客的评论系统
cover: cover.png
categories: '技术'
tags: ['博客', '评论', 'Giscus']
date: 2026-08-03 09:30:00
---

## 为什么是 Giscus

先说一个悲伤的故事。我之前用的是 [Valine](https://github.com/xCss/Valine)，后端挂在 LeanCloud 上。有一天评论突然全部消失了，控制台报错 `Code 504: The app is archived`——LeanCloud 的免费版应用长期不活跃会被**归档**，整个评论系统就这么凉了。数据还躺在云端，但恢复要花钱花时间，评论量也不大，索性直接换。

[Giscus](https://giscus.app/) 把评论直接存进 **GitHub Discussions**，它的好处是：

- **零后端**：没有服务器、没有数据库，也就没有归档这种破事（除非 GitHub 跑路）
- **评论即 Discussion**：管理评论就是管理 GitHub 仓库，还能被 GitHub 搜索检索到
- **与 GitHub Pages 天生一对**：博客部署在 GitHub Pages，评论也住在 GitHub，一家人不用两边跑

工作原理大致是这样的：

<img src="giscus原理.svg" alt="Giscus 工作原理示意图" width="80%" height="80%">

## 准备工作

Giscus 需要三个前置条件，都在 GitHub 上操作：

1. **启用 Discussions**：仓库 `Settings` → `General` → `Features` → 勾选 Discussions（没启用的话 `/discussions` 会 404）
2. **安装 giscus app**：访问 https://github.com/apps/giscus → `Install` → 授权给你的博客仓库
3. **获取配置参数**：打开 https://giscus.app/ 配置器，输入仓库名，选一个 Discussion 分类（比如 `Announcements`），页面会生成一段配置代码，里面有三个参数待会儿要用：`data-repo`、`data-repo-id`、`data-category-id`

小技巧：`repo_id` 不一定要通过配置器拿，直接调 GitHub API 也行：`GET https://api.github.com/repos/{owner}/{repo}`，返回的 `id` 字段就是。

## 集成 Giscus

本站用的是 Hexo + Butterfly 主题，主题自带 Giscus 支持，配置都在 `_config.butterfly.yml` 里。

第一步，把评论系统切到 Giscus：

```yaml
comments:
  use: Giscus
```

第二步，填上 `giscus` 段：

```yaml
giscus:
  repo: chestnut19981123/chestnut19981123.github.io
  repo_id: R_kgDOMEsqYw
  category_id: DIC_kwDOMEsqY84DCi_i
  theme:
    light: light
    dark: dark
  option:
    data-mapping: title
```

> ⚠️ 注意：上面是本站的真实参数，仅作示例。请通过 giscus.app 配置器生成你自己的 `repo`、`repo_id`、`category_id` 再填入——不然评论区会挂到别人的仓库上，两边都尴尬。

`theme` 里的 `light` / `dark` 会让评论区自动跟随博客的明暗模式，不用自己管。`option` 里的 `data-mapping` 决定评论和文章的关联方式，详见下一节。

如果用的不是 Butterfly，也可以直接把 giscus.app 生成的 `<script>` 塞进页面，效果一样。

## 踩坑：评论对不上号

Giscus 有几种把评论关联到文章的方式（`data-mapping`）：`pathname`、`title`、`og:title`、`specific` 等，官方默认是 `pathname`——按页面 URL 关联。

我们一开始用的就是 `pathname`，但用了一段时间发现两个问题。一是 **GitHub 的 Discussions 列表里每条讨论的标题都是一串 URL**，完全看不出对应哪篇文章，管理起来很痛苦；二是 **URL 一旦变化就对不上号了**——以后要是改了 permalink 结构，旧讨论就跟新页面失联，评论看起来像"丢"了。

所以后来把 `data-mapping` 改成了 `title`：

```yaml
option:
  data-mapping: title
```

Discussion 标题直接就是文章标题，在 GitHub 上一眼就能认出哪条讨论对应哪篇文章。代价是文章标题不能重复——对个人博客来说基本不是问题。

## 管理评论

评论管理直接去仓库的 **Discussions** 页面：编辑、删除、锁定、置顶都可以，甚至可以把有价值的讨论变成下一篇文章的素材。

邮件通知也不用像 Valine 那样自己搭一个 Valine-Admin 了：在 Discussions 里订阅（Watch）相关分类，或者对某篇文章的 Discussion 点订阅，有人评论时 GitHub 会通过网页、邮件、APP 任意方式通知你。

## 遗留问题

- **旧评论没了**：Valine 没有迁移到 Giscus 的通道，加上 LeanCloud 处于归档态，恢复成本高于评论本身的价值，旧评论就随它去吧（数据还在云端，真想恢复也还是可以的）
- **侧边栏"最新评论"**：主题的这个组件数据源是 Valine 的 API，切到 Giscus 后主题会自动隐藏它，不用手动处理

就这样，祝你的评论区也能用上十年不凉的系统。🎉
