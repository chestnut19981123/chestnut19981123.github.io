---
title: 基于Valine部署博客的评论系统
cover: cover.png
categories: '技术'
tags: ['博客', '评论', 'Valine']
date: 2024-06-05 20:35:03
---

[Valine](https://github.com/xCss/Valine) 是一个基于 LeanCloud 的评论系统，主打一个快速、简单、免费。本站的评论区最初就是它——不过现在已经退役了，换成 [Giscus](https://giscus.app/)（[部署记录在这](/b8a788f7a6c1/)）。退役原因嘛，LeanCloud 免费版应用一旦长期不活跃就会被归档，整个评论区直接凉凉，别问我是怎么知道的。这篇文章是当年的部署记录，想用 Valine 的同学可以参考。

## 集成Valine

集成方式很简单，参考[官方文档](https://valine.js.org/)就行。如果你用的是 Hexo，大多数主题都自带评论支持——本站的 `hexo-theme-butterfly` 只需简单配置即可，具体见[这里](https://butterfly.js.org/posts/ceeb73f/#%E8%A9%95%E8%AB%96)。

Valine 的后端是 [LeanCloud](https://www.leancloud.cn/)，在控制台创建一个名为 `blog-comment` 的应用就能开工。之后想管理、删除评论，去 `数据存储`-`结构化数据`-`Comment</>` 就行。

![LeanCloud管理界面](LeanCloud管理界面.png)

## 邮件通知

有人评论了，总得有人知道吧？邮件通知安排上。[Valine-Admin](https://github.com/DesertsP/Valine-Admin) 是常用的方案，但我在部署它的时候直接报错——项目太久没更新，作者大概已经忘了它。好在有热心网友的 [fork 版本](https://github.com/wiidede/Valine-Admin)，我们就用这个。

部署过程全程可视化：进入 LeanCloud 控制台，在 `云引擎`-`管理部署` 里新建一个分组（比如 `EmailValineAdmin`）：

![LeanCloud新建分组](LeanCloud新建分组.png)

然后进到部署的 `设置` 里添加环境变量，参考下图即可（云引擎域名可有可无）。其中 `SMTP_PASS` 需要去邮箱申请：以 QQ 邮箱为例，在 `设置`-`账号`-`POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务` 里开启服务并获取授权码，中间会经历手机验证等一系列折腾。别嫌麻烦，这是整个部署里最费劲的一步。

![自定义环境变量](自定义环境变量.png)

各变量的含义如下表（最容易翻车的一步，建议对着填）：

| 变量          | 示例                   | 说明 |
| --            | --                     | --   |
| SITE_NAME     | Deserts                | [必填]博客名称
| SITE_URL      | https://panjunwen.com  | [必填]首页地址
| SMTP_SERVICE  | QQ                     | [必填]邮件服务提供商，支持QQ、163、126、Gmail以及更多
| SMTP_USER     | xxxxxx@qq.com          | [必填]SMTP登录用户
| SMTP_PASS     | xxxxxxxx               | [必填]SMTP登录密码（QQ邮箱需要获取独立密码）
| SENDER_NAME   | Deserts                | [必填]发件人
| SENDER_EMAIL  | xxxxxx@qq.com          | [必填]发件邮箱
| ADMIN_URL     | https://xxx.leanapp.cn/| [建议]Web主机二级域名（云引擎域名），用于自动唤醒
| BLOGGER_EMAIL | xxxxx@gmail.com        | [可选]博主通知收件地址，默认使用SENDER_EMAIL
| AKISMET_KEY   | xxxxxxxx               | [可选]Akismet Key 用于垃圾评论检测，设为MANUAL_REVIEW开启人工审核，留空不使用反垃圾

环境变量就位后，`部署` 里选 Git 部署，仓库地址填 `https://github.com/wiidede/Valine-Admin`，分支 `master`，点部署：

![部署到生产环境](部署到生产环境.png)

部署日志里出现成功提示就成了。要是失败了也别慌，换别的 fork 仓库再试一次，总有一款能跑。

成功之后测一下：A 在文章里评论 → 站长（`BLOGGER_EMAIL`）收到提醒；A 回复了 B → 站长和 B 都会收到邮件。收到邮件的那一刻，成就感拉满。

## 管理回复

部署时指定了域名的话，可以用可视化界面管理评论，参考[这里](https://github.com/DesertsP/Valine-Admin#%E8%AF%84%E8%AE%BA%E7%AE%A1%E7%90%86)。没指定域名也没关系——直接去 LeanCloud 的 `数据存储`-`结构化数据`-`Comment</>` 里管理。个人博客评论量本就不多，后一种方法完全够用，甚至有点大材小用。

以上就是 Valine 的全部部署流程。最后再唠叨一句：如果不想体验"评论系统突然凉凉"的心跳加速，可以考虑一开始就用 [Giscus](https://giscus.app/)——评论直接存在 GitHub Discussions 里，没有后端，也就没有归档这回事。
