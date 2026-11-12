---
title: ember-rsi 全景：把「改进」做成可复现的实验
categories: 'AI'
tags: ['AI', 'Agent', 'RSI', 'ember-rsi', '自演进']
date: 2026-11-12
cover: cover.svg
description: ember-rsi 的野心不是优化一个 Agent，而是让任何 AI 产物——提示词、推理服务配置、Triton 算子——都能接进同一套 RSI 循环。本文从 Make Everything RSI-able 出发，拆开它的五个角色、三种目标和最小可运行实验。
---

## 开场：三套脚本，一个循环

假设你手上同时有三摊改进任务：

- Agent 团队想改提示词和 Skill，让 Agent 更会干活；
- 推理团队想调 batch size、并行度这些服务参数，让吞吐更高；
- 算子团队想改 Triton 内核，让它在目标 shape 上更快。

三拨人各自写了一套改进脚本。打开一看，骨架几乎一模一样：

**生成候选 → 跑评测 → 比较分数 → 留下更好的 → 再来一轮。**

不一样的是零件：Agent 团队评任务通过率，推理团队看吞吐和延迟，算子团队查正确性和耗时。一样的是循环：都要有基线，都要能提交候选，都要有评测，都要决定选谁。

于是问题来了：**每换一个目标，是不是都要把这套循环再抄一遍？**

抄一遍还不算最糟。更糟的是三套脚本各存各的记录：这个候选从哪来、当时跑了哪些任务、分数是多少，换一个人就得重新问一遍。所谓「效果好了很多」，最后往往只剩一句玄学分享。

[ember-rsi](https://github.com/evolving-foundry/ember-rsi) 的答案不是「再做一个更强的 Agent」，而是把这套循环本身做成框架。它的 tagline 只有一句：

> Multiple self-improvement strategies in one framework · Make Everything RSI-able.
>
> 多种自演进策略，一个框架统一承载；后半句才是重点：让一切皆可 RSI。

这不是说模型会突然顿悟，也不是说所有东西都值得自我改进。它说的是：**RSI 循环不应该和某个具体目标绑死。** 只要一个目标能被标识、被提议、被测量、被选择，它就应该能接进同一套循环。

ember-rsi 是 evolving-foundry 开源的 RSI 实验框架，Apache-2.0，目前还是个 0.x 项目。它不训练模型，也不替 Agent 写业务代码；它提供一套 RSI Core，让不同的目标、策略和插件通过 Configuration 组合起来。

## 命题：Make Everything RSI-able 到底在说什么

先把「RSI-able」拆开。一个目标要进入 RSI 循环，至少需要四件事：

1. **可标识**：有基线、有候选，能说清哪一版是哪一版；
2. **可提议**：有一个候选生成器，能从当前版本变出下一版；
3. **可测量**：有一组任务和指标，能比较两版的好坏；
4. **可选择**：有一个规则，决定留下哪一版。

ember-rsi 把这四件事抽象成 **Application、Proposer、Evaluator、Selector**，再用 Policy 串成流程，用 Runtime 记录事实。目标适配器不是写死在框架里的，而是一个插件。

![RSI-able 的四个条件](fig-rsi-able.svg)

所以它的内置目标可以长得很不一样：

| 目标 | 改什么 | 评什么 |
| --- | --- | --- |
| Agent Harness | 提示词 / Skill | 任务通过率 |
| 推理服务 | 服务参数 | 吞吐 / 延迟 |
| Triton 算子 | 算子源码 | 正确 / 性能 |

三者的技术栈几乎没有任何共同点，Application 和 Evaluator 也各不相同，但进入框架的方式一样：定义一个 Application，给出 baseline 和 Target，绑定一个 Proposer 和一个 Evaluator，再选一个 Selector。剩下的循环由 Runtime 跑。

架构文档里有一句话，基本就是「Everything」的架构版本：

> The same RSI Core can run different Experiments with different Configurations.
>
> 同一套 RSI Core 可以通过不同的 Configuration 运行不同的 Experiment。

注意这里的因果：不是框架里预置了一堆 `if (target === 'harness')` 的分支，而是目标和策略都被抽象成了可替换的配置。如果每加一个目标就要改核心，那叫「支持很多目标」；只有核心不变、目标可插拔，才配叫「Everything」。

## 角色：目标和策略是两根轴

ember-rsi 把一次实验拆成五个角色。名字有点多，但分工很干净——每个角色只回答一个问题：

| 角色 | 一句话职责 |
| --- | --- |
| **Application** | 目标适配器：决定「改进什么」 |
| **Policy** | 改进策略：决定「怎么改进」 |
| **Plugin** | 能力实现：决定「谁来干活」 |
| **Recipe** | 装配单：决定「这一次跑什么」 |
| **Runtime / Manager** | 执行核心：保证「跑过什么有据可查」 |

前两个角色分别管「改什么」和「怎么改」，后三个负责把它们装起来、跑起来。

![五个角色与 Recipe 装配关系](fig-roles.svg)

这五个角色里，最容易看错的是 Recipe。它不是一个和 Application、Policy 并列的盒子，而是那张装配单本身：`application` 是字段，`policy` 是引用，`bindings` 是接线表。三者合起来，才是一次实验。

Recipe 上的 `application` 和 `policy` 是两根正交的轴。换 `application`，换的是优化对象——同一份 Policy 可以今天改 Agent Bundle，明天改推理服务，后天改算子；换 `policy`，换的是改进策略——同一个 Harness 目标可以用 Harness² 做多提案者组合，也可以用 WikiSkill 做训练/验证/测试，也可以用 GEPA 做 Pareto 搜索，而 `application` 不用动。一个决定「改什么」，一个决定「怎么改」；两者不绑死，才有「同一套 RSI Core 跑不同实验」这件事。

先看目标这根轴。Application 是目标适配器，不是目标本身。它不关心你改的是提示词还是算子，只关心四件事：基线（baseline）是什么、可改范围（Target）有哪些、候选（candidate）怎么提交、评测实例（instance）怎么准备和释放。所以「改 Agent」和「改 Triton 算子」在框架眼里是同一类事——都是找一个 Application，把这四件事讲清楚。内置的 Agent Bundle、Inference、Kernel 就是三份现成适配器；目标不在这里，也可以自己写一份。

再看策略这根轴。Policy 是一份 `rsi.policy/v1` 的 YAML 数据流，不实现能力，只负责编排：什么时候调用插件、怎么保存状态、在什么条件下分支、循环几次、什么时候停。同一个 Policy 可以绑定不同的插件实现，流程一行都不用改。

Plugin 是能力，不是流程。这里有个容易混淆的规则：一个插件只实现一个公共契约，同一个契约可以有多个插件实现。拿 Agent 后端举例：`contract.agent` 是契约，Pi、Codex、Claude Code、DSH 是四份实现。Policy 的 `require` 只声明「这里需要一个 Agent 实现」，Recipe 的 `bindings` 再决定用哪一份；想从 Pi 换到 Codex，只改绑定，Policy 不动。Proposer 这边也一样，只是名字更容易骗人：`proposer.grid` 和 `proposer.pareto-evolution` 都带 `proposer.` 前缀，实现的却不是 `contract.proposer`，而是各自的专门契约——输入、输出和状态机不一样，契约自然也不一样。插件 ID 是「谁」，契约是「它遵守哪套输入输出」，两者不是一回事。

最后是 Runtime。它是执行核心，负责候选、测量、实例租约、检查点与恢复；你不需要在 Policy 里手写「记录候选血缘」或「释放实例」。「这个候选从哪来、当时跑了哪些任务、分数是多少」由它统一回答，换一个人、下一次实验，也能接着跑。

五个角色说全了，再回看「Everything is a plugin」：它不只是指目标。Application、Policy、Proposer、Evaluator、Selector、Agent 后端、Memory、Reflection，全部通过契约接入，可以替换。外部插件放进 `~/.ember-rsi/plugins/`，或者运行时加 `--plugin-dir`，和内置组件走同一套注册机制。契约是插座，插件是电器，Recipe 是插线板，Policy 是用电说明书；一个电器只插一个插座，但同一个插座可以换不同的电器。

## 循环：三种目标，一套流程

角色摆好，实验本身就是一个很朴素的循环：

![同一个闭环，换目标不换流程](fig-loop.svg)

以 Harness² 为例：

1. **基线先跑一遍。** 没有基线，后面所有「更好」都只是形容词。
2. **Proposer 提修改。** Invariant Proposer 和 Domain Proposer 各自提一版改进，Compose 再把它们合成一个候选。
3. **Application 校验并提交。** 改动必须落在 Target 允许的范围内；空改动会返回 `no-change`。
4. **Evaluator 跑任务。** 结果写成 Measurement：执行状态、覆盖率、评测条件、指标、证据引用。
5. **Selector 比较候选。** 可以按数值指标选，也可以把交付物匿名摆出来让模型评审。
6. **记录并进入下一轮。** 候选有父候选，测量有证据引用，调用有记录。

把这条流水线横着切，会发现三种目标只是换了零件：

- **提案**：Harness² 用 Proposer 改提示词、Skill；基础设施用 Grid/Optuna 给参数组合，或用 Operator Proposer 改源码。
- **提交**：AgentBundle 提交候选；Inference 提交配置；Kernel 提交源码。
- **评测**：AgentBench 跑任务；InferenceBench 测吞吐、延迟；OperatorBench 查正确性、耗时。
- **选择**：Harness² 匿名比较交付物；基础设施按指标 + 约束、正确性 + 性能选择。

同一套循环，换的是 Application、Proposer、Evaluator、Selector；不变的是候选、测量、选择、记录这些环节。

这也是为什么候选血缘值得单独说一句。每次改进不是覆盖上一版，而是从父候选分叉出一个新版本：

![候选血缘：分叉与测量](fig-lineage.svg)

像 git，只是每条分支都自带体检报告。你随时可以回答「这个候选是从哪来的、改了哪些文件、当时跑了哪几个任务、分数是多少」。这些事实不是为了审计而审计，而是为了让下一轮、下一次实验、下一个人能接着跑。

## 约束：循环怎么防止自欺

「Everything」听起来很宏大，但 RSI 循环有一个古老的风险：模型既提方案又下结论，最后变成自己给自己打分的行为艺术。

ember-rsi 的处理方式是把「提议」和「事实」分开：

- **候选提案**要过 Schema 和 Target：形状对不对，路径许不许。越权就拒绝，连候选记录都不落。
- **评测结果**要过 Schema 和测量校验：指标、证据引用、评测条件是否齐全，能不能和基线比较。
- **反思修订**要过 Revision 授权和版本控制：改的资源在不在授权名单里，通过后才在当前实验中激活。

这里的「证据」不是法庭上的证据，而是 Runtime 在运行过程中保存下来的材料：执行轨迹、日志、交付物等。插件要总结经验、更新 Memory 或做反思，读的就是这些材料。麻烦在于材料里同时混着「过程」和「分数」——如果负责学习的插件能看到测试集分数，它就会朝着分数过拟合。所以证据按可见范围分成三档，插件声明自己用哪一档，Runtime 就只给它这一档：

| 证据视图 | 可见内容 | 用途 |
| --- | --- | --- |
| `execution` | 脱敏执行轨迹；不含分数、Reward 和判题反馈 | 总结经验 |
| `training-summary` | 执行轨迹 + 训练分数 + 有界评测反馈 | 训练/验证学习 |
| `delivery` | 只有交付物内容，例如 `report.md` | 交付质量评审 |

Harness² 的 Memory 用 `execution`：每个任务结束后，用执行轨迹更新经验，供后续任务的 Proposer 使用。WikiSkill 更严格：10 个任务分成 6 个训练、2 个验证、2 个测试；训练阶段可以用 `training-summary` 学习，候选必须通过验证门，测试集只在学习全部结束后跑一次，分数不回流到任何学习步骤。

这些机制不是「Everything」的主线，但它们决定了 RSI 循环会不会变成自欺循环。目标可以换，策略可以换，事实不能造假。

## 门槛：一个文件，一个谓词

要证明「RSI-able」的门槛有多低，看 ember-rsi 自带的 minimal 示例就够了。它放在 `skills/ember-rsi/assets/minimal/`，完全不需要模型、Docker 或网络，只做一件事：把一句话塞进提示词。

- 基线 `prompt.md` 只有一行：`Return the answer without checking it.`
- 确定性 Proposer 把 `prompt.md` 改写为 `Check the answer before returning it.`
- Evaluator 检查 `prompt.md` 里有没有 `Check the answer` 这个精确子串，有就是 1 分，没有就是 0 分。
- Target 只允许修改 `prompt.md`，`bundle.yaml`、`agent.yaml`、`dependencies.lock` 都是保护文件。
- Selector 按 `checkPhrase` 指标取最大值。
- 全程不调用模型，评测只是字符串匹配。

Recipe 的关键部分长这样：

```yaml
schemaVersion: rsi.recipe/v1
id: recipe.skill-search
application:
  plugin: application.agentbundle
  config:
    target: { schema: ./target.yaml }
    baseline: { directory: ./baseline }
policy:
  id: policy.skill-search
  config: { maxRounds: 2 }
bindings:
  proposer: { plugin: proposer.skill-fixed, config: {} }
  evaluator: { plugin: evaluator.skill-text, config: {} }
  selector:
    { plugin: selector.metric, config: { metric: checkPhrase, direction: maximize } }
```

从源码检出的话，先运行 `pnpm install --frozen-lockfile && pnpm build`。构建只生成 CLI，不会把它装进 PATH，所以在仓库根目录用 `pnpm ember-rsi` 调用；已经全局链接过的话，也可以直接写 `ember-rsi`。然后把示例复制到工作区，依次运行：

```sh
# 复制最小示例到工作区
cp -r skills/ember-rsi/assets/minimal .rsi/skill-demo
# 检查 Recipe、插件和运行前提
pnpm ember-rsi doctor .rsi/skill-demo/recipe.yaml --plugin-dir .rsi/skill-demo/extension
# 跑实验，实验 ID 指定为 skill-demo-01
pnpm ember-rsi run .rsi/skill-demo/recipe.yaml --plugin-dir .rsi/skill-demo/extension --id skill-demo-01
# 查看实验记录
pnpm ember-rsi show skill-demo-01
# 独立验收：会另建一个带时间戳的实验
node .rsi/skill-demo/run.mjs
```

`run.mjs` 用断言把关键结果逐条核对一遍：

- 实验状态是 `succeeded`；
- 两个候选，一个有 `parentRef: null`，一个是它的子候选；
- 两条测量，分数排序后是 `[0, 1]`；
- 两个实例，状态都是 `released`；
- 选中候选的 `checkPhrase` 是 1；
- 全程没有模型调用；
- 第二轮提案写回同样的内容，Application 报 `no-change`，不会产生重复测量；
- 恢复一个已成功的实验，测量数量仍然是 2。

跑完在 dashboard 里打开本次实验就能复查：Candidates 页的 `From` 列是父候选，Measurements 页有 2 条记录，Call history 里点 `Proposer / R2` 能看到 `no-change`；Overview 的 Model calls 显示未记录。实例状态和 resume 不重放看 `run.mjs` 的输出：`releasedInstances: 2`、`successfulResumeDidNotReplay: true`。

实际跑出来，脚本最后打印的是：

```json
{
  "id": "skill-1794467440005",
  "status": "succeeded",
  "scores": [0, 1],
  "candidates": 2,
  "releasedInstances": 2,
  "successfulResumeDidNotReplay": true
}
```

`run.mjs` 不会接着 `skill-demo-01` 跑，而是自己新建一条实验：ID 用时间戳生成（形如 `skill-1794467440005`），记录也写在它自己的 `.rsi/skill-demo/.rsi` 下，所以打印的 ID 和 `skill-demo-01` 不同。`show` 记录里的 usage 是 12 次操作、2 次评测运行。

![最小 RSI 目标：一个文件，一个谓词](fig-minimal.svg)

这个实验证明不了 Agent 变聪明。它证明的是另一件事：**一个可标识、可提议、可测量、可选择的目标，哪怕只有一个文件，也能进入同一套 RSI 循环。** 把它放大，就是 Agent Bundle 的很多文件 + AgentBench，是推理服务的一份配置 + InferenceBench，是算子的源码 + OperatorBench。

先确认循环能接住最小的目标，再往里放真实的目标。顺序反了，你得到的可能是一台很贵的随机数发生器。

## 边界：接口意义上的 Everything

ember-rsi 不是 benchmark，不是模型，也不是部署工具。它不会替你定义「好」的标准，也不会保证搜索一定找到更好的候选。

它能保证的是：如果你声称一个候选更好，这个声称有基线、有评测条件、有证据、有记录，别人可以复查。

「Make Everything RSI-able」也不是「一键让万物进化」。它有两层边界：

第一，**目标必须可测量。** 如果一件事没有可重复的评测方式，框架帮不了你。评测器是整套系统的天花板：如果评测器只会数关键词，你最终会得到一个很会数关键词的 Agent。

第二，**真实目标有真实成本。** Harness² 的示例用 10 个任务，k=1 时需要 40 次评测运行；WikiSkill 的示例同样是 10 个任务，训练/验证/测试三阶段跑下来，在基础设施重试之前就有 28 次任务尝试，还需要 Docker 和 Terminal-Bench 镜像；算子搜索需要 Triton-Ascend 和 NPU 环境；推理参数搜索需要一个能启动的推理服务。这些是目标本身的成本，不是框架的成本。

所以更准确的说法是：**「Everything」是接口意义上的 Everything，不是「所有东西都值得 RSI」。** 值得 RSI 的东西，不必再重写一套框架；不值得 RSI 的东西，套上框架也不会突然值得。

RSI 不是魔法，它只是把「改进」拆成可替换的目标、可替换的策略，和必须诚实记录的事实。

## 收尾：把循环留下来

回到开头那三拨人。他们真正重复的不是评测脚本，而是同一套循环：生成候选、跑评测、比较分数、留下更好的、再来一轮。ember-rsi 做的事情，是把这套循环从具体目标里抽出来：Application 决定改什么，Policy 决定怎么改，Plugin 提供能力，Recipe 把它们装成一次实验，Runtime 负责把发生过的事情记下来。于是换目标只需换 `application`，换策略只需换 `policy`，循环本身不用重写。

当然，循环能跑起来，不等于它值得信。候选要过 Schema 和 Target，测量要能复查，反思修订要过授权；证据按可见范围分档，免得负责学习的插件直接盯着测试分数过拟合。候选不是覆盖上一版，而是从父候选分叉，每条分支都带着自己的 Measurement。这些机制不宏大，但它们决定了 RSI 是在改进，还是在自欺。

最小的例子把门槛压到了一个文件和一条子串匹配：一个可标识、可提议、可测量、可选择的目标，就能进入同一套循环。但门槛低不代表万物都值得 RSI。目标必须可测量，评测器是整套系统的天花板，真实目标也有真实成本。所谓 Make Everything RSI-able，是接口意义上的 Everything：值得 RSI 的东西不必再写一套框架，不值得 RSI 的东西套上框架也不会突然值得。

RSI 不是魔法。它只是把「改进」拆成可替换的目标、可替换的策略，和必须诚实记录的事实。下次再有人说「我这版提示词感觉更好」，你可以问他：这套循环，能换个目标再跑一遍吗？

---

项目地址：[github.com/evolving-foundry/ember-rsi](https://github.com/evolving-foundry/ember-rsi)
