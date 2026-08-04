# 博客背景特效重构 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将博客背景特效从「动态彩带 + 烟花」调整为「粒子连线 + 烟花」，纯配置改动。

**Architecture:** 仅修改 Hexo 根目录的 `_config.butterfly.yml`（Butterfly 主题配置文件）。开启内置 canvas_nest 粒子连线（深蓝色），关闭 canvas_fluttering_ribbon 动态彩带，fireworks 保留不动。不新增/修改任何其他文件，不触碰 themes/butterfly submodule 内部文件。

**Tech Stack:** Hexo 7.3 + Butterfly 主题（git submodule），配置文件 `_config.butterfly.yml`。

## Global Constraints

- 只允许修改 `_config.butterfly.yml` 一个文件（`docs/` 下文档除外）
- 禁止修改 `themes/butterfly/` 内的任何文件（该目录是 git submodule，改动会污染 gitlink）
- 粒子颜色必须为 `'70,140,220'`（深蓝），不得用默认 `'0,0,255'`
- 保持现有配置的注释风格（注释为繁体中文，保留原注释行）
- 部署靠 CI：push 到 `main` 触发 GitHub Actions；本地不执行 `npm run deploy`

---

### Task 1: 修改背景特效配置并验证

**Files:**
- Modify: `_config.butterfly.yml`（canvas_nest 段与 canvas_fluttering_ribbon 段，位于文件中「Background effects (背景特效)」区块，约 700-715 行）

**Interfaces:**
- Consumes: 无（这是本计划唯一任务）
- Produces: 修改后的 `_config.butterfly.yml`，以及可 grep 验证的 `public/` 构建产物

- [ ] **Step 1: 初始化主题 submodule（若尚未初始化）**

```bash
[ -d themes/butterfly/layout ] || git submodule update --init
```

Expected: 命令静默成功；`ls themes/butterfly/layout` 存在。若 `node_modules/hexo` 缺失则补 `npm install`。

- [ ] **Step 2: 读取配置文件对应段落**

用 Read 工具读取 `_config.butterfly.yml` 的「Background effects (背景特效)」区块（约 690-720 行），确认当前值与下方一致：

```yaml
canvas_fluttering_ribbon:
  enable: true
  mobile: false

# canvas_nest
# https://github.com/hustcc/canvas-nest.js
canvas_nest:
  enable: false
  color: '0,0,255' #color of lines, default: '0,0,0'; RGB values: (R,G,B).(note: use ',' to separate.)
```

- [ ] **Step 3: 关闭动态彩带**

Edit `_config.butterfly.yml`，精确替换（保留 `mobile: false` 行不变）：

```
old:  canvas_fluttering_ribbon:
        enable: true
new:  canvas_fluttering_ribbon:
        enable: false
```

- [ ] **Step 4: 开启粒子连线并设为深蓝**

Edit `_config.butterfly.yml`，精确替换（其余行 opacity/zIndex/count/mobile 不动）：

```
old:  canvas_nest:
        enable: false
        color: '0,0,255' #color of lines, default: '0,0,0'; RGB values: (R,G,B).(note: use ',' to separate.)
new:  canvas_nest:
        enable: true
        color: '70,140,220' #color of lines, default: '0,0,0'; RGB values: (R,G,B).(note: use ',' to separate.)
```

- [ ] **Step 5: 构建并验证配置生效**

```bash
npm run build
```

Expected: 构建成功无报错。然后验证主题确实按配置渲染了特效脚本（Butterfly 按 enable 值决定是否注入对应 JS）：

```bash
grep -ril "canvas-nest" public/ | head -5   # Expected: 至少 1 个文件命中（粒子脚本被注入）
grep -ril "fluttering" public/              # Expected: 无输出（彩带脚本未注入）
```

若 canvas-nest 未命中：检查 `themes/butterfly/scripts/events/` 下 inject.js 中该特效的脚本名写法（可能是 `canvas_nest`），改用实际写法重试 grep。若 fluttering 仍有命中：确认 `_config.butterfly.yml` 中 enable 已改为 false，并检查是否有其他段（如 `canvas_ribbon`）也引用了该脚本——注意 canvas_ribbon（静止彩带）是另一个独立开关，本次不动，若它仍 enable: false 则属正常。

- [ ] **Step 6: 本地起服务器供用户目视确认**

```bash
npm run server
```

Expected: 服务器在 http://localhost:4000 启动。请用户在浏览器确认：(a) 首页背景出现深蓝粒子连线；(b) 动态彩带消失；(c) 点击页面任意位置仍有烟花；(d) 窗口缩窄到移动端宽度时粒子不出现。用户确认后 Ctrl-C 停掉服务器。

- [ ] **Step 7: 提交**

```bash
git add _config.butterfly.yml
git commit -m "更新背景特效：开启粒子连线，关闭动态彩带

Co-Authored-By: Claude <noreply@anthropic.com>"
```

Expected: 提交成功，工作区干净。**注意**：只 add `_config.butterfly.yml`；`themes/butterfly` 若显示为 modified（submodule 拉取后出现未跟踪内容）属正常，不要 add 它。

- [ ] **Step 8: 推送与部署说明**

```bash
git push origin dev
```

（部署无需手动操作：合并到 `main` 后 GitHub Actions 自动构建发布。）
