---
title: 多 Agent 实现原理：两个臭皮匠，顶不顶一个诸葛亮
categories: 'AI'
tags: ['AI', 'Agent', '多智能体']
date: 2026-10-23 16:00:00
cover: cover.svg
description: 拆解多 Agent 的实现机制——子 Agent 就是一个会递归的工具调用，它卖的不是更多脑子而是更多注意力预算；并说明读、写操作各自该怎么编排。
---

## 开场：先把它拆开

多 Agent 这两年很热，但真动手的人常卡在同一个地方：**它到底是怎么实现的，什么时候值得用。**

这个话题上被引用最多的几篇工程总结，结论看着还挺矛盾。Cognition（做 Devin 的那家）2025 年 6 月发过一篇[《Don't Build Multi-Agents》](https://cognition.com/blog/dont-build-multi-agents)，标题就是结论；Anthropic 的[多 Agent 调研系统](https://www.anthropic.com/engineering/multi-agent-research-system)则报告说，Opus 4 当主管、Sonnet 4 当子 Agent，在他们内部的调研评测上比单 Agent 高出 **90.2%**。十个月后 Cognition 又补了一篇[《Multi-Agents: What's Actually Working》](https://cognition.com/blog/multi-agents-working)，把话说细了。

这几篇材料后面还会引用到，但它们的分歧本身不是这篇的主题——**真正值得搞清楚的是分歧底下那个技术约束**。下面按三步拆：

- **实现**：多 Agent 到底是什么（剧透：不是新物种，就是一个会递归的工具）
- **价值**：它真正在卖什么（剧透：不是"多个脑子"，是"多份注意力预算"）
- **边界**：什么任务能用，什么任务纯属烧钱

## 实现：一个会递归的工具

### 核心循环：一个循环，一份消息列表

一个 Agent，说到底就是**一个循环，加一份消息列表**。伪代码如下：

```python
messages = [system_prompt, user_request]

while True:
    response = llm(messages)            # 1. 推理：模型决定下一步

    if not response.tool_use:           # 2. 没有工具请求 → 任务完成
        break

    for tool in response.tool_use:      # 3. 执行：宿主调用工具
        result = host.execute(tool)     #    （此处可能触发权限确认）

    messages.append(result)             # 4. 观察：结果喂回，下一轮
```

模型自己碰不到文件系统，它只会输出一段 JSON 说"我要读 `kafka.md`"。真正动手的是宿主：解析 JSON、调用对应函数、把结果回填成一条消息。所以一个"工具"，本质是**声明 + 执行**的绑定体——声明（JSON Schema）发给模型看，执行（一个回调函数）攥在宿主手里。

现在关键的一问来了：**谁规定那个执行函数不能是一整个 Agent？**

### 子 Agent：第二个循环，第二份上下文

没有任何规定。你在宿主里写下这么个函数：

```python
def spawn_agent(role: str, task: str) -> str:
    """派一个子 Agent 去干一件独立的事。"""
    cfg = ROLES[role]
    answer, _, _ = run_agent(cfg["system"], task, cfg["tools"])
    return answer          # ← 只把最后那句话交回去
```

`run_agent` 就是上面那个循环。于是这个"工具"被调用时，宿主不是去读个文件，而是**又开了一个 Agent 循环**。

这就是多 Agent 的全部秘密。它不是什么新架构、新协议、新物种——它就是一个工具，只不过这个工具的实现体里递归了一次。

![普通工具与子 Agent 工具的执行路径对比](fig-recursion.svg)

看左边，`read_doc` 被调用时，宿主的执行体直接返回文件内容。看右边，`spawn_agent` 被调用时，宿主的执行体里长出了**第二个循环、第二份消息列表**。

这个递归结构白送了三个性质，一个都不用额外设计：

**第一，对主循环来说它毫无特殊性。** 在真实的调度表里，它和读文件躺在同一行：

```python
TOOLBOX = {"list_docs": list_docs, "read_doc": read_doc, "spawn_agent": spawn_agent}
```

主循环那个 `for tool in response.tool_use` 分支根本不知道自己在调起一个子 Agent。它只知道自己调了个函数、拿回一个字符串、回填进消息列表。

**第二，子 Agent 天然有独立上下文。** 因为 `run_agent` 里第一行就是新建一份 `messages`。子 Agent 看不到主 Agent 说过什么、读过什么——这不是谁特意设计的隔离，是递归的自然结果。要让它看见，反而得额外写代码把上下文传进去。

**第三，交回来的只有最后那句话。** 子 Agent 中间读了多少文件、试了多少条路、走了多少弯路，全留在它自己那份 `messages` 里，跟着函数一起返回、一起被丢掉。回到主 Agent 上下文的，只有 `answer` 这一个字符串。

### 真实产品：Claude Code 怎么定义子 Agent

Claude Code 的子 Agent 就是这么回事。一个子 Agent 就是一个 Markdown 文件加一段 YAML frontmatter：

```markdown
---
name: code-reviewer
description: Reviews code for quality and best practices
tools: Read, Glob, Grep
model: sonnet
---

You are a code reviewer. When invoked, analyze the code and provide
specific, actionable feedback on quality, security, and best practices.
```

注意 `tools` 和 `model` 两个字段。子 Agent 可以有**自己的一套工具**，还可以**换一个更便宜的模型**——"臭皮匠"这个词就是这么来的：诸葛亮（贵模型）当主管，臭皮匠（便宜模型）去跑腿。

Claude Code 的[官方文档](https://code.claude.com/docs/en/sub-agents)里有一句话，把这一节讲的东西全概括了：

> Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions.
>
> 每个子 Agent 都在自己的上下文窗口里运行，有自定义的系统提示词、专属的工具集和独立的权限。

一句话里有四样东西是它自己的：**上下文窗口、系统提示词、工具集、权限**。子 Agent 在自己的上下文里干活，只把摘要交回来。

### 并行：白送的能力

既然子 Agent 只是个工具，那"同时派三个"这件事就变得很平常：一轮里模型请求了多个 `spawn_agent`，宿主用线程池一起跑就行——把上面伪代码里的第 3 步换成并行版本，其余一字不动：

```python
pending = response.tool_use             # 这一轮模型要的东西，可能不止一件

if len(pending) > 1 and all(t.name == "spawn_agent" for t in pending):
    with ThreadPoolExecutor(max_workers=len(pending)) as pool:
        results = pool.map(host.execute, pending)   # 几个子 Agent 一起跑
else:
    results = [host.execute(t) for t in pending]    # 其余情况照旧一个个来

for result in results:                  # 4. 观察：结果喂回，下一轮
    messages.append(result)
```

调研系统那份报告说，这一步把复杂查询的调研时间砍掉了**最多 90%**。他们的做法是主管一次拉起 3-5 个子 Agent，每个子 Agent 再并行调 3 个以上的工具。

到这里，多 Agent 的机制部分就讲完了。真的就这么点东西。难的不是怎么让它跑起来，是**判断什么时候该让它跑**——这才是后面几节要解决的问题。

## 注意力预算：它真正卖的是什么

先把一个常见的误解拆掉：多 Agent 不是因为"三个脑子比一个脑子聪明"才有效。

调研系统那份报告里有个相当反直觉的数据：用 BrowseComp（专门测"能不能找到难以发现的信息"的评测）做分析，**光是 token 用量就解释了 80% 的性能差异**，再加上工具调用次数和模型选择，三个因素合起来解释了 95%。

报告的原话是 "Multi-agent systems work mainly because they help spend enough tokens to solve the problem."（多 Agent 之所以有效，主要是因为**它帮你把 token 花出去**）。

听起来像在骂人，其实是句大实话。问题在于：为什么"多花 token"会变聪明？

### 上下文腐烂：为什么多花 token 会变聪明

《Multi-Agents: What's Actually Working》那篇给了个更底层的解释，叫它 **Context Rot（上下文腐烂）**：

> Models usually have a limited number of attention heads, and when they need to work on a growing context of instructions, prompts, code, etc, important details may not be fully incorporated into its decision-making.
>
> 模型通常只有数量有限的注意力头，当它需要在一个不断增长的上下文（指令、提示词、代码等等）上工作时，重要的细节可能无法被充分纳入决策。

一个 Agent 干得越久，上下文里堆的东西越多：读过的一堆文件、跑过的一堆命令、试错留下的残骸、中途的推理过程。这些东西大部分在**当下这一步**毫无用处，但它们照样占着注意力。

子 Agent 的价值就在这儿：它是一块**干净的小画布**。它不知道主管之前试错过什么，也不需要知道——它只拿到一个明确的任务，在一个干净的上下文里把这件事做完，然后交回一句结论。

所以多 Agent 卖的不是"更多脑子"，是**更多份互不污染的注意力预算**。

### 实测：主管的上下文省了一半

光讲道理不够，跑个数看看。任务是从九份产品资料里做一次消息队列选型，两种跑法：

**单 Agent 模式**——主管自己一份一份读：

```text
═══ 模式：single ═══
任务：公司要引入一个消息队列，请翻阅 docs/ 下的资料，给出选型建议。

  [主管] list_docs → 回填 217 字
  [主管] read_doc → 回填 318 字
  [主管] read_doc → 回填 381 字
  [主管] read_doc → 回填 327 字
  [主管] read_doc → 回填 275 字
  [主管] read_doc → 回填 326 字
  [主管] read_doc → 回填 309 字
  [主管] read_doc → 回填 336 字
  [主管] read_doc → 回填 381 字
  [主管] read_doc → 回填 306 字

─── 主管上下文里累积的工具结果：3176 字 ───
```

九份资料，一个字不落全进了主管的上下文。**3176 字。**

**多 Agent 模式**——主管派三个研究员分头读，再派一个评审：

```text
═══ 模式：multi ═══
任务：公司要引入一个消息队列，请翻阅 docs/ 下的资料，给出选型建议。

  [主管] list_docs → 回填 217 字
  [主管] spawn_agent → 回填 256 字
  [主管] spawn_agent → 回填 338 字
  [主管] spawn_agent → 回填 446 字
  [主管] spawn_agent → 回填 201 字

  ── 子 Agent 明细 ──
  researcher   读进去  1023 字  →  交回  446 字
  researcher   读进去  1243 字  →  交回  256 字
  researcher   读进去   910 字  →  交回  338 字
  reviewer     读进去     0 字  →  交回  201 字

─── 主管上下文里累积的工具结果：1458 字 ───
```

![单 Agent 与多 Agent 的上下文占用对比](fig-context.svg)

子 Agent 合计还是读了 3176 字——**一份没少读**。但主管的上下文只涨了 1458 字，其中还有 217 字是那份文件清单。

这个 2.2 倍听起来不算惊艳，因为这是个玩具例子：资料一共才三千字，每个研究员只读了三个小文件。调研系统那份报告说，真实调研里一个子 Agent 要跑 10-15 次工具调用，每次返回的是几千 token 的网页正文——那时候的差距是数量级的，不是两三倍。

### 摘要：省了注意力，也让你瞎了

别高兴太早。子 Agent 交回来的是**摘要**，摘要意味着有损压缩。

它读了三份资料，觉得其中某条细节不重要，没写进结论——那条细节对主管来说就等于不存在了。主管没有任何办法知道它漏了什么，因为它从来没看见过原文。

这是多 Agent 的根本代价，而且它和上一节的好处是同一个机制的两面：**独立上下文让你省了注意力，也让你瞎了。**

所以子 Agent 的任务描述必须写清楚"你要输出什么"。调研系统那边在这上面栽过跟头：一开始让主管给子 Agent 发很简短的指令，比如"研究一下半导体短缺"，结果子 Agent 要么误解任务，要么几个子 Agent 做了完全重复的搜索——一个在查 2021 年的汽车芯片危机，另外两个在查 2025 年的供应链，谁也没覆盖全。

## 隐含决策：写操作会打架

子 Agent 能并行，但**不是所有操作都能并行**。这条界线画在哪儿，《Don't Build Multi-Agents》立的两条原则里，第二条给了答案：

> **Principle 2: Actions carry implicit decisions, and conflicting decisions carry bad results.**
>
> 行动携带隐含决策，而互相冲突的决策会带来糟糕的结果。

那篇里举的例子是让两个子 Agent 分别写一个 Flappy Bird 游戏的一部分：一个做小鸟，一个做背景。两个子 Agent 看不到对方在干什么，于是各自在无数个**没人指定过的细节**上做了选择——配色、线条粗细、像素风格。最后拼起来，鸟和背景的美术风格完全不搭。

![两个并行写操作的隐含决策互相冲突](fig-conflict.svg)

关键词是"隐含"。你没让子 Agent 决定配色，但它在写代码的过程中**不得不**决定，因为总得写个具体颜色上去。这个决定是行动自带的副产品，不是任务书里写着的。

于是问题就清楚了：**读操作不携带隐含决策，写操作携带。**

- 子 Agent 去查一份资料、回来给段总结——它没有改变世界的状态，没有做出任何需要和别人对齐的决定。三个研究员分头查资料，查完汇总，天经地义。
- 子 Agent 去写一个模块——它在每一个没被指定的角落都留下了自己的选择。三个子 Agent 并行写，等于三套互不知情的选择在同一个代码库里撞车。

调研系统那份报告里还有一句很容易被忽略的话。在讲完 90.2% 的提升之后，紧接着承认：

> most coding tasks involve fewer truly parallelizable tasks than research, and LLM agents are not yet great at coordinating and delegating to other agents in real time.
>
> 大多数编码任务里真正能并行的部分比调研少，而且今天的 LLM Agent 还不太擅长实时地互相协调和委派。

注意这句话里的两个限制：**能并行的部分更少**——写操作要排队；**实时协调还不够**——隐含决策对不齐。这两条正是下面两节的内容。

## 能用的形态：写操作单线程

《Multi-Agents: What's Actually Working》的结论可以压成一句话：

> multi-agent systems work best today when **writes stay single-threaded** and the additional agents **contribute intelligence rather than actions**.
>
> 今天多 Agent 系统效果最好的形态是：写操作保持单线程，额外的 Agent 贡献的是**智能**而不是**行动**。

读操作可以随便并行，写操作必须排成一队。在这个约束下，他们找到了几种真的能用的形态。

### 评审：干净上下文抓得更多

Devin Review 是他们最反直觉的发现。让一个模型审自己写的代码，你大概会觉得没用——但它平均每个 PR 能抓出 **2 个 bug**，其中约 **58% 是严重问题**（逻辑错误、漏掉的边界情况、安全漏洞）。

更反直觉的是他们的调优结论：

> Interestingly, we found this technique to work best when the coding and review agents do not share any context beforehand.
>
> 我们发现这个技术**在编码 Agent 和评审 Agent 事先完全不共享上下文时效果最好**。

为什么？两个原因。

一是**被迫从头推理**。评审 Agent 看不到需求文档，只能从实现反推意图，于是它会去质疑那些编码 Agent 因为"用户就是这么说的"而放过去的东西——比如用户让它实现一个不安全的模式，编码 Agent 照做了，评审 Agent 会问一句"这真的对吗"。

二是**上下文腐烂**。编码 Agent 干了好几个小时，上下文里塞满了读过的仓库、跑过的命令、试过的方案、修过的错误。评审 Agent 跳过这一切，只看 diff，需要什么上下文自己现读。上下文短了，注意力集中了，反而更能发现细微的问题。

这正好接上「注意力预算」那节：**干净上下文不是"顺带的好处"，它本身就是能力。**

### 聪明朋友：小模型什么时候该问大模型

第二个形态是反过来用：便宜的小模型当主力，遇到难题时去问一个贵的大模型。

那篇里提到在 Windsurf 上做过一个实验——让 SWE-1.5（950 tok/s 的次前沿模型）当主力，遇到棘手情况就调用 Sonnet 4.5。核心难题有两个：

**小模型怎么知道自己到极限了？** 这个方向反过来了：做委派决定的不再是那个更聪明的模型。他们的办法是鼓励主力 Agent 至少问一次，以及针对特定场景写死规则——比如"遇到合并冲突必须问"。

**该传多少上下文过去？** 传少了，聪明模型做不出充分判断。他们试出来的 80/20 解法是：**把主力的完整上下文 fork 一份过去**，然后让主力问宽泛的问题（"我该怎么办？"），由聪明模型自己决定该聊什么。

顺便说，他们坦白了结局：SWE-1.5 当主力还不够格，这个实验没成。**写出来的失败比写出来的成功更有信息量**，这也是那篇文章值得读的原因。

### 主管：只管范围，不做决定

主管 Agent 负责协调子 Agent 的**范围**，而不是替它们做决定。拆任务、划边界、汇总结果——决策权不分散。

## 四种编排：谁跟谁说话

把上面这些整理成拓扑图，能用的多 Agent 结构其实就四种。

![四种多 Agent 编排拓扑](fig-topology.svg)

| 拓扑 | 谁读谁写 | 适合什么 | 现实例子 |
| --- | --- | --- | --- |
| **主管-工人** | 工人只读，主管只写 | 可并行的信息收集、宽搜型调研 | 调研系统 |
| **流水线** | 逐段交接，写操作串行 | 有明确阶段划分的长流程 | 需求 → 设计 → 编码 |
| **生成-验证** | 一个写，一个只读着审 | 需要挑错的产出 | Devin Review |
| **群聊/辩论** | 人人可读可写 | 理论上最像开会，实践中最难 | 学术原型居多 |

前三种都有明确的"谁说了算"，第四种没有。有一份总结对第四种说得很直接：

> agents today are not quite able to engage in this style of long-context proactive discourse with much more reliability than you would get with a single agent.
>
> 今天的 Agent 还不太能进行这种长上下文的主动讨论，可靠性并不比单 Agent 更高。

他们的类比很到位：人类工程师发现代码冲突，正确的做法是**谈一谈，达成共识**。这个"谈一谈"看起来很轻松，其实需要相当高的智能——人能把最重要的信息高效地传达给对方，这个"高效"本身就是本事。今天的模型还不太会。等它学会了，并行度会再上一个台阶。

## 三张账单：什么时候别用

多 Agent 不是免费的。在动手之前，先看看这三张账单。

### token 账单：15 倍的溢价

调研系统那份报告的数据很实在：普通对话里的 Agent 大约用掉聊天 **4 倍**的 token，而多 Agent 系统用掉聊天 **15 倍**的 token。

他们的结论也很实在："For economic viability, multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."——多 Agent 要求任务本身的价值足够高，高到能付得起这笔溢价。

换句话说：**如果这个任务的产出不值 15 倍的钱，那它就不该用多 Agent。** 用一句"帮我查个函数在哪"去启动一个多 Agent 系统，是纯粹的浪费。

### 协调账单：别指望它自己控规模

调研系统早期踩的坑很典型：Agent 会给简单查询生成 **50 个子 Agent**，会无休止地在网上找根本不存在的来源，会互相用频繁的进度更新干扰对方。

他们最后的解法是在提示词里写死规模规则：

- **简单事实查找**：1 个 Agent，3-10 次工具调用
- **直接对比**：2-4 个子 Agent，每个 10-15 次调用
- **复杂调研**：10 个以上子 Agent，职责明确划分

注意这是**写在提示词里的**。模型自己判断不出"这个任务该花多大力气"，你得告诉它。这条经验在任何多 Agent 系统里都适用：**别指望主管 Agent 自己学会控制规模。**

### 调试账单：难度的平方

单 Agent 已经够难调了，多 Agent 是难度的平方。

报告的原话是 "Agents make dynamic decisions and are non-deterministic between runs, even with identical prompts."（同样的提示词，两次跑出来不一样）。他们举的例子是：有用户反馈"Agent 找不到明显的信息"，而团队完全看不出为什么：是搜索词不好？是选错了来源？是工具挂了？最后是靠**完整的生产链路追踪**才定位到问题。

另一份总结还补了一刀，关于那些看起来很燃的 demo——20 万行代码的浏览器、10 万行的 C 编译器、优化 LLM 训练脚本：

> These are exciting but they all share a property most real software doesn't: a simple, verifiable success criterion.
>
> 它们都有一个共同点，而大多数真实软件没有：**一个简单、可验证的成功标准**。

浏览器能编译通过、C 编译器能编译 C 代码，这是二元的、可自动判定的。而真实的软件要的是"放大人类的品味和决策"——那是一个完全不同的目标，多 Agent 并行写在这个目标下只会把品味撕成几份。

### 判断表：什么任务配什么结构

| 你的任务 | 建议 |
| --- | --- |
| 宽搜型调研、多源信息收集 | ✅ 主管-工人，工人只读 |
| 需要挑错的产出（代码、文案、方案） | ✅ 生成-验证，评审用干净上下文 |
| 有明确阶段的长流程 | ✅ 流水线，写操作串行 |
| 并行写同一份产出 | ❌ 隐含决策会撞车 |
| 任务产出不值 15 倍 token | ❌ 直接单 Agent |
| 需要实时来回讨论才能推进 | ❌ 今天的模型还不会开会 |

## 收尾：一句话的判据

回到标题那个问题：两个臭皮匠，顶不顶一个诸葛亮？

答案是——**看他们干什么活**。让他们分头去打听消息，三个臭皮匠确实顶一个诸葛亮，而且快得多；让他们一起动手改同一份东西，那就不只是顶不上，还会互相拆台，最后按 15 倍的价格收你钱。

这个"看干什么活"，落到实现上就是三句话：

- **只读的任务**：并行度越高越好，子 Agent 越多越宽
- **要写的任务**：写操作排成一队，让额外的 Agent 只贡献智能、不贡献行动
- **产出不值 15 倍 token 的任务**：别用

多 Agent 不生产智能，它生产的是**注意力预算**；而它的实现，说到底就是一个会递归的工具调用。这笔预算怎么花，才是真正需要你判断的事。
