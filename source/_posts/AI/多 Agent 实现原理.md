---
title: 多 Agent 实现原理：两个臭皮匠，顶不顶一个诸葛亮
categories: 'AI'
tags: ['AI', 'Agent', '多智能体']
date: 2026-10-23 16:00:00
cover: cover.svg
description: 拆解多 Agent 的实现机制——子 Agent 就是一个会递归的工具调用，它卖的不是更多脑子而是更多注意力预算；并给出可运行的最小实现，以及读/写操作各自该怎么编排。
---

## 开场：先把它拆开

多 Agent 这两年很热，但真动手的人常卡在同一个地方：**它到底是怎么实现的，什么时候值得用。**

这个话题上被引用最多的两份工程总结，结论看着还挺矛盾。Cognition（做 Devin 的那家）2025 年 6 月发过一篇[《Don't Build Multi-Agents》](https://cognition.com/blog/dont-build-multi-agents)，标题就是结论；Anthropic 的[多 Agent 调研系统](https://www.anthropic.com/engineering/multi-agent-research-system)则报告说，Opus 4 当主管、Sonnet 4 当子 Agent，在他们内部的调研评测上比单 Agent 高出 **90.2%**。十个月后 Cognition 又补了一篇[《Multi-Agents: What's Actually Working》](https://cognition.com/blog/multi-agents-working)，把话说细了。

这两份材料后面还会引用到，但它们的分歧本身不是这篇的主题——**真正值得搞清楚的是分歧底下那个技术约束**。下面按三步拆：

- **实现**：多 Agent 到底是什么（剧透：不是新物种，就是一个会递归的工具）
- **价值**：它真正在卖什么（剧透：不是"多个脑子"，是"多份注意力预算"）
- **边界**：什么任务能用，什么任务纯属烧钱

## 一、实现：一个会递归的工具

### 先回忆一个 Agent 长什么样

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

### 于是就有了子 Agent

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
TOOLBOX = {"list_docs": list_docs, "read_doc": read_doc,
           "spawn_agent": spawn_agent}
```

主循环那个 `for tool in response.tool_use` 分支根本不知道自己在调起一个子 Agent。它只知道自己调了个函数、拿回一个字符串、回填进消息列表。

**第二，子 Agent 天然有独立上下文。** 因为 `run_agent` 里第一行就是新建一份 `messages`。子 Agent 看不到主 Agent 说过什么、读过什么——这不是谁特意设计的隔离，是递归的自然结果。要让它看见，反而得额外写代码把上下文传进去。

**第三，交回来的只有最后那句话。** 子 Agent 中间读了多少文件、试了多少条路、走了多少弯路，全留在它自己那份 `messages` 里，跟着函数一起返回、一起被丢掉。回到主 Agent 上下文的，只有 `answer` 这一个字符串。

### 真实产品里长什么样

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

官方文档里有两句话，把这一节讲的东西全概括了：

> Each subagent runs in its own context window with a custom system prompt, specific tool access, and independent permissions.
>
> ——[Claude Code 文档](https://code.claude.com/docs/en/sub-agents)

第一句是"独立上下文"，第二句更直白：**子 Agent 在自己的上下文里干活，只把摘要交回来。**

### 并行是白送的

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

Anthropic 说这一步把复杂查询的调研时间砍掉了**最多 90%**。他们的做法是主管一次拉起 3-5 个子 Agent，每个子 Agent 再并行调 3 个以上的工具。

到这里，多 Agent 的机制部分就讲完了。真的就这么点东西。难的不是怎么让它跑起来，是**判断什么时候该让它跑**——这才是后面几节要解决的问题。

## 二、它真正卖的是什么：注意力预算

先把一个常见的误解拆掉：多 Agent 不是因为"三个脑子比一个脑子聪明"才有效。

Anthropic 在那篇博客里给了一个相当反直觉的数据：在他们用 BrowseComp（专门测"能不能找到难以发现的信息"的评测）做的分析里，**光是 token 用量就解释了 80% 的性能差异**，再加上工具调用次数和模型选择，三个因素合起来解释了 95%。

他们的原话是："Multi-agent systems work mainly because they help spend enough tokens to solve the problem."——多 Agent 之所以有效，主要是因为**它帮你把 token 花出去了**。

听起来像在骂人，其实是句大实话。问题在于：为什么"多花 token"会变聪明？

### 因为上下文会腐烂

Cognition 在 2026 那篇里给了一个更底层的解释，他们叫它 **Context Rot（上下文腐烂）**：

> 模型通常只有数量有限的注意力头，当它需要在一个不断增长的上下文（指令、提示词、代码等等）上工作时，重要的细节可能无法被充分纳入决策。

一个 Agent 干得越久，上下文里堆的东西越多：读过的一堆文件、跑过的一堆命令、试错留下的残骸、中途的推理过程。这些东西大部分在**当下这一步**毫无用处，但它们照样占着注意力。

子 Agent 的价值就在这儿：它是一块**干净的小画布**。它不知道主管之前试错过什么，也不需要知道——它只拿到一个明确的任务，在一个干净的上下文里把这件事做完，然后交回一句结论。

所以多 Agent 卖的不是"更多脑子"，是**更多份互不污染的注意力预算**。

### 实测一下

光讲道理不够，跑个数看看。我写了个最小实现，任务是从九份产品资料里做一次消息队列选型，两种跑法：

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

这个 2.2 倍听起来不算惊艳，因为这是个玩具例子：资料一共才三千字，每个研究员只读了三个小文件。Anthropic 说真实调研里一个子 Agent 要跑 10-15 次工具调用，每次返回的是几千 token 的网页正文——那时候的差距是数量级的，不是两三倍。

### 但摘要是有损的

别高兴太早。子 Agent 交回来的是**摘要**，摘要意味着有损压缩。

它读了三份资料，觉得其中某条细节不重要，没写进结论——那条细节对主管来说就等于不存在了。主管没有任何办法知道它漏了什么，因为它从来没看见过原文。

这是多 Agent 的根本代价，而且它和上一节的好处是同一个机制的两面：**独立上下文让你省了注意力，也让你瞎了。**

所以子 Agent 的任务描述必须写清楚"你要输出什么"。Anthropic 在这上面栽过跟头：他们一开始让主管给子 Agent 发很简短的指令，比如"研究一下半导体短缺"，结果子 Agent 要么误解任务，要么几个子 Agent 做了完全重复的搜索——一个在查 2021 年的汽车芯片危机，另外两个在查 2025 年的供应链，谁也没覆盖全。

## 三、写操作会打架

子 Agent 能并行，但**不是所有操作都能并行**。这条界线画在哪儿，Cognition 那篇立的两条原则里，第二条给了答案：

> **Principle 2: Actions carry implicit decisions, and conflicting decisions carry bad results.**
>
> ——行动携带隐含决策，而互相冲突的决策会带来糟糕的结果。

Cognition 举的例子是让两个子 Agent 分别写一个 Flappy Bird 游戏的一部分：一个做小鸟，一个做背景。两个子 Agent 看不到对方在干什么，于是各自在无数个**没人指定过的细节**上做了选择——配色、线条粗细、像素风格。最后拼起来，鸟和背景的美术风格完全不搭。

![两个并行写操作的隐含决策互相冲突](fig-conflict.svg)

关键词是"隐含"。你没让子 Agent 决定配色，但它在写代码的过程中**不得不**决定，因为总得写个具体颜色上去。这个决定是行动自带的副产品，不是任务书里写着的。

于是问题就清楚了：**读操作不携带隐含决策，写操作携带。**

- 子 Agent 去查一份资料、回来给段总结——它没有改变世界的状态，没有做出任何需要和别人对齐的决定。三个研究员分头查资料，查完汇总，天经地义。
- 子 Agent 去写一个模块——它在每一个没被指定的角落都留下了自己的选择。三个子 Agent 并行写，等于三套互不知情的选择在同一个代码库里撞车。

这也解释了 Anthropic 那篇里一句很容易被忽略的话。他们在吹完 90.2% 的提升之后，紧接着承认：

> most coding tasks involve fewer truly parallelizable tasks than research, and LLM agents are not yet great at coordinating and delegating to other agents in real time.
>
> ——大多数编码任务里真正能并行的部分比调研少，而且今天的 LLM Agent 还不太擅长实时地互相协调和委派。

注意这句话里的两个限制：**能并行的部分更少**——写操作要排队；**实时协调还不够**——隐含决策对不齐。这两条正是下面两节的内容。

## 四、能用的形态：写操作单线程

Cognition 在第二篇里的结论可以压成一句话：

> multi-agent systems work best today when **writes stay single-threaded** and the additional agents **contribute intelligence rather than actions**.
>
> ——今天多 Agent 系统效果最好的形态是：写操作保持单线程，额外的 Agent 贡献的是**智能**而不是**行动**。

读操作可以随便并行，写操作必须排成一队。在这个约束下，他们找到了几种真的能用的形态。

### 形态一：干净上下文的评审

Devin Review 是他们最反直觉的发现。让一个模型审自己写的代码，你大概会觉得没用——但它平均每个 PR 能抓出 **2 个 bug**，其中约 **58% 是严重问题**（逻辑错误、漏掉的边界情况、安全漏洞）。

更反直觉的是他们的调优结论：

> 我们发现这个技术**在编码 Agent 和评审 Agent 事先完全不共享上下文时效果最好**。

为什么？两个原因。

一是**被迫从头推理**。评审 Agent 看不到需求文档，只能从实现反推意图，于是它会去质疑那些编码 Agent 因为"用户就是这么说的"而放过去的东西——比如用户让它实现一个不安全的模式，编码 Agent 照做了，评审 Agent 会问一句"这真的对吗"。

二是**上下文腐烂**。编码 Agent 干了好几个小时，上下文里塞满了读过的仓库、跑过的命令、试过的方案、修过的错误。评审 Agent 跳过这一切，只看 diff，需要什么上下文自己现读。上下文短了，注意力集中了，反而更能发现细微的问题。

这正好接上第二节：**干净上下文不是"顺带的好处"，它本身就是能力。**

### 形态二：聪明朋友

第二个形态是反过来用：便宜的小模型当主力，遇到难题时去问一个贵的大模型。

Cognition 在 Windsurf 上试过——让 SWE-1.5（950 tok/s 的次前沿模型）当主力，遇到棘手情况就调用 Sonnet 4.5。核心难题有两个：

**小模型怎么知道自己到极限了？** 这个方向反过来了：做委派决定的不再是那个更聪明的模型。他们的办法是鼓励主力 Agent 至少问一次，以及针对特定场景写死规则——比如"遇到合并冲突必须问"。

**该传多少上下文过去？** 传少了，聪明模型做不出充分判断。他们试出来的 80/20 解法是：**把主力的完整上下文 fork 一份过去**，然后让主力问宽泛的问题（"我该怎么办？"），由聪明模型自己决定该聊什么。

顺便说，他们坦白了结局：SWE-1.5 当主力还不够格，这个实验没成。**写出来的失败比写出来的成功更有信息量**，这也是那篇文章值得读的原因。

### 形态三：主管只管范围

主管 Agent 负责协调子 Agent 的**范围**，而不是替它们做决定。拆任务、划边界、汇总结果——决策权不分散。

## 五、四种编排：谁跟谁说话

把上面这些整理成拓扑图，能用的多 Agent 结构其实就四种。

![四种多 Agent 编排拓扑](fig-topology.svg)

| 拓扑 | 谁读谁写 | 适合什么 | 现实例子 |
| --- | --- | --- | --- |
| **主管-工人** | 工人只读，主管只写 | 可并行的信息收集、宽搜型调研 | Anthropic Research |
| **流水线** | 逐段交接，写操作串行 | 有明确阶段划分的长流程 | 需求 → 设计 → 编码 |
| **生成-验证** | 一个写，一个只读着审 | 需要挑错的产出 | Devin Review |
| **群聊/辩论** | 人人可读可写 | 理论上最像开会，实践中最难 | 学术原型居多 |

前三种都有明确的"谁说了算"，第四种没有。Cognition 对第四种的态度很直接：

> agents today are not quite able to engage in this style of long-context proactive discourse with much more reliability than you would get with a single agent.
>
> ——今天的 Agent 还不太能进行这种长上下文的主动讨论，可靠性并不比单 Agent 更高。

他们的类比很到位：人类工程师发现代码冲突，正确的做法是**谈一谈，达成共识**。这个"谈一谈"看起来很轻松，其实需要相当高的智能——人能把最重要的信息高效地传达给对方，这个"高效"本身就是本事。今天的模型还不太会。等它学会了，并行度会再上一个台阶。

## 六、实现：把上面这些接起来

前面讲的机制，在配套脚本 `multi_agent_mini.py` 里刚好能连起来。它一共就六部分：环境、普通工具、核心循环、`spawn_agent`、工具声明、两种跑法。核心循环和《Agent 实现原理》里那个是同一个，多出来的只有 `spawn_agent` 那十几行。

它没有做上下文压缩、没有做失败重试、没有做流式输出，子 Agent 的轮数上限也是写死的——适合动手理解原理，不适合直接拿去当生产框架。

有一处名字上的出入先说清楚：《[Agent 实现原理](/c8c2406b1e62/)》那套伪代码用的是 Claude API 的叫法（`response.tool_use`、`tool_use_id`），而这个脚本走 OpenAI 兼容接口，同一批东西叫 `msg.tool_calls`、`tc.id`。**是同一件事的两种拼写**，下面代码一律用脚本里的拼写。

### 环境

需要 Python 3.10 以上和 `openai` 包。脚本通过兼容接口调用模型，凭证填进 `.env`，不要提交到版本库。脚本的简易加载器不处理引号、变量展开和多行值，所以配置值直接写，不加引号。

```bash
python -m venv .venv
source .venv/bin/activate
pip install openai
```

```text
OPENAI_BASE_URL=你的兼容接口地址
OPENAI_API_KEY=你的接口凭证
CHAT_MODEL=该接口支持的模型名称
```

资料放在脚本旁的 `docs/` 目录，按产品分子目录，每个目录里放若干 Markdown。本文用的是三个消息队列产品的调研笔记，纯属教学示例。

### 代码

第一段是环境和两个普通工具。注意 `list_docs` 会把完整路径列出来——这不是多余的，模型看不见文件系统，你不告诉它文件叫什么，它就只能瞎猜文件名然后一次次撞墙。

```python
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

def load_env() -> None:
    env_path = Path(__file__).parent / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

load_env()
client = OpenAI(
    base_url=os.environ["OPENAI_BASE_URL"],
    api_key=os.environ["OPENAI_API_KEY"],
)
MODEL = os.environ["CHAT_MODEL"]
DOCS = Path(__file__).parent / "docs"

TASK = "公司要引入一个消息队列，请翻阅 docs/ 下的资料，给出选型建议。"

# 记录每个子 Agent 吃进去多少、交回来多少
SUBAGENT_STATS: list[tuple[str, int, int]] = []
```

第二段是核心循环。这是全文最重要的二十行——**主 Agent 和子 Agent 调的是同一个函数**，区别只在传进去的参数。

```python
def list_docs() -> str:
    """列出所有资料，按产品目录分组，给出可直接用于 read_doc 的路径。"""
    lines = []
    for d in sorted(p for p in DOCS.iterdir() if p.is_dir()):
        lines.append(f"{d.name}/")
        for f in sorted(d.glob("*.md")):
            lines.append(f"  {d.name}/{f.name}")
    return "\n".join(lines)

def read_doc(name: str) -> str:
    path = DOCS / name
    if not path.exists():
        return f"没有这个文件：{name}"
    return path.read_text(encoding="utf-8")
```

第三段是 `spawn_agent` 和它的角色表。整个多 Agent 的"魔法"就在这七行里：新开一份 `messages`，跑完只把最后那句话交回去。

```python
def chat(messages: list, tools: list):
    """调一次模型。tools 为空时不传 tools 参数。"""
    kwargs = {"model": MODEL, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    return client.chat.completions.create(**kwargs).choices[0].message

def run_agent(system: str, task: str, tools: list,
              max_turns: int = 16, tag: str = "agent"):
    """一个 Agent 就是「一个循环 + 一份消息列表」。

    返回 (最终回答, 喂进本上下文的工具结果字符数, 日志行)。
    子 Agent 和主 Agent 调的是同一个函数——区别只在参数。
    """
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": task},
    ]
    fed_chars = 0
    log: list[str] = []

    for _ in range(max_turns):
        msg = chat(messages, tools)
        messages.append(msg)

        if not msg.tool_calls:                       # 没有工具请求 → 收工
            return msg.content, fed_chars, log

        # 一次请求多个 spawn_agent → 并行跑（这是多 Agent 提速的来源）
        parallel = (len(msg.tool_calls) > 1
                    and all(tc.function.name == "spawn_agent"
                            for tc in msg.tool_calls))

        def run_one(tc):
            args = json.loads(tc.function.arguments or "{}")
            out = TOOLBOX[tc.function.name](**args)
            if not isinstance(out, str):
                out = json.dumps(out, ensure_ascii=False)
            return tc, out

        if parallel:
            with ThreadPoolExecutor(max_workers=len(msg.tool_calls)) as pool:
                results = list(pool.map(run_one, msg.tool_calls))
        else:
            results = [run_one(tc) for tc in msg.tool_calls]

        for tc, out in results:
            fed_chars += len(out)
            log.append(f"[{tag}] {tc.function.name} → 回填 {len(out)} 字")
            messages.append({"role": "tool", "tool_call_id": tc.id,
                             "content": out})

    return "（达到轮数上限）", fed_chars, log
```

第四段是工具声明，也就是发给模型的"牌面"。最后一行是全文的题眼：`spawn_agent` 和 `read_doc` 躺在同一张表里，对循环来说毫无区别。

```python
def spawn_agent(role: str, task: str) -> str:
    """这就是多 Agent 的全部秘密：一个工具，实现体里又开了一个循环。

    新开一份 messages，跑完只把最后那句话交回去——中间过程留在它自己的
    上下文里，不回填给调用者。
    """
    cfg = ROLES[role]
    answer, fed, _ = run_agent(cfg["system"], task, cfg["tools"], tag=role)
    SUBAGENT_STATS.append((role, fed, len(answer)))
    return answer

ROLES = {
    "researcher": {
        "system": (
            "你是一名技术调研员。用 read_doc 把指定目录下的资料**全部读完**，"
            "然后输出不超过 150 字的结论：只讲事实与权衡，不要客套话。"
        ),
        "tools": [],          # 稍后填
    },
    "reviewer": {
        "system": (
            "你是一名严格的技术评审。你只能看到一份结论，看不到它依据的原始资料。"
            "请指出：哪些说法缺依据、哪些权衡被略过、有没有过度断言。"
            "只输出问题清单，不超过 150 字。"
        ),
        "tools": [],
    },
}
```

最后一段是两种跑法的对比。**唯一的区别是主管手里有没有 `spawn_agent` 这个工具。**

```python
def fn(name, desc, props, required):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props,
                       "required": required}}}

READ_TOOLS = [
    fn("list_docs", "列出 docs/ 下有哪些产品目录", {}, []),
    fn("read_doc", "读取一份资料的全部内容",
       {"name": {"type": "string",
                 "description": "资料路径，如 kafka/01-定位与吞吐.md"}},
       ["name"]),
]

SPAWN_TOOL = fn(
    "spawn_agent",
    "派一个子 Agent 去干一件独立的事。它在自己的上下文里干活，"
    "只把最终结论交回来，中间过程不占用你的上下文。",
    {"role": {"type": "string", "enum": ["researcher", "reviewer"],
              "description": "子 Agent 的角色"},
     "task": {"type": "string", "description": "交代清楚的任务，含目录名和输出要求"}},
    ["role", "task"],
)

ROLES["researcher"]["tools"] = READ_TOOLS

# 关键：spawn_agent 和 read_doc 躺在同一张表里，对循环来说毫无区别。
TOOLBOX = {"list_docs": list_docs, "read_doc": read_doc,
           "spawn_agent": spawn_agent}

SINGLE_SYSTEM = """你是技术选型小组的负责人。你可以自己用 list_docs / read_doc 翻阅资料。
请把 docs/ 下所有产品目录里的资料都读完，然后给出一份不超过 250 字的选型建议，
说清推荐谁、为什么、什么情况下不推荐。"""

MULTI_SYSTEM = """你是技术选型小组的负责人。你手下有研究员，用 spawn_agent 派活。
请先 list_docs 看清有哪些产品，然后为每个产品各派一名研究员（role 填 researcher），
让他们分头去读该目录下的全部资料，你只收结论。
收齐结论后，写一份不超过 250 字的选型建议，说清推荐谁、为什么、什么情况下不推荐。
最后再派一名 reviewer 审你自己的这份建议，并把它提的问题附在最终回答后面。"""

def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "multi"

    if mode == "single":
        system, tools, tag = SINGLE_SYSTEM, READ_TOOLS, "主管"
    else:
        system, tools, tag = MULTI_SYSTEM, READ_TOOLS + [SPAWN_TOOL], "主管"

    print(f"═══ 模式：{mode} ═══")
    print(f"任务：{TASK}\n")

    answer, fed, log = run_agent(system, TASK, tools, tag=tag)

    for line in log:
        print("  " + line)

    if SUBAGENT_STATS:
        print("\n  ── 子 Agent 明细 ──")
        for role, ate, gave in SUBAGENT_STATS:
            print(f"  {role:12s} 读进去 {ate:5d} 字  →  交回 {gave:4d} 字")

    print(f"\n─── 主管上下文里累积的工具结果：{fed} 字 ───\n")
    print(answer)

if __name__ == "__main__":
    main()
```

```bash
python multi_agent_mini.py single   # 主管自己读
python multi_agent_mini.py multi    # 派研究员 + 评审
```

<details>
<summary>展开配套资料：三个产品的调研笔记</summary>

以下九份资料按 `docs/<产品>/<序号>-<主题>.md` 存放。内容是教学示例，不是选型依据——真要选消息队列请自己查文档。

`docs/kafka/01-定位与吞吐.md`：

```text
# Kafka · 定位与吞吐

Kafka 最初是 LinkedIn 的日志管道，现在常被当成分布式提交日志（distributed commit log）来用。
核心抽象是「分区 + 追加写」：每条消息落到某个分区尾部，消费者靠 offset 记录自己读到哪。

顺序写盘加零拷贝，单分区就能跑到很高的吞吐。批量（batch）和压缩（lz4/zstd）是吞吐的两大来源，
但批得越久，单条消息的端到端延迟越高。典型配置下 P99 延迟在几十毫秒量级。

分区是并行的单位。生产者按 key 哈希选分区，同一个 key 永远落同一个分区，
所以「同一订单的事件有序」这种要求能靠 key 满足；代价是热点 key 会把单个分区压垮。
```

`docs/kafka/02-运维成本.md`：

```text
# Kafka · 运维成本

依赖 ZooKeeper 的时代已经过去，KRaft 模式把元数据管理收进了 broker 自己，
部署少了一套组件。但要自己管的东西仍然不少：broker 集群、分区再均衡、磁盘水位。

分区数是个容易踩的坑。分区只能在创建时定，或者做有限的扩容操作，
而且扩容之后 key 到分区的映射会变——原本有序的同 key 消息可能被拆到不同分区。
所以分区数要一次留够余量，不能等业务涨上来再加。

磁盘水位要盯紧。保留策略按时间或体积，磁盘写满会直接拖垮 broker。
托管方案（Confluent Cloud、各云厂商的 Kafka 服务）能省掉大部分运维，
但按量计费在大流量下账单很可观。

监控重点是消费延迟（lag）。lag 持续上涨说明消费能力跟不上生产，
要么加消费者，要么加分区——而加分区又要回到上面那个坑。
```

`docs/kafka/03-适用场景.md`：

```text
# Kafka · 适用场景

**日志采集与事件管道。** 这是它的老本行。多下游各自独立消费同一份数据，
互不影响，加一个新下游不用动上游。

**事件溯源与重放。** 消息按时间保留（比如 7 天），消费完不删，消费者可以回拨 offset
重放历史。这让「补数据」「重跑下游」「新下游追历史」都变得容易，
也是它和传统队列最大的区别。

**流式 ETL。** 配合 Flink / Kafka Streams 做实时聚合，是常见组合。

**不适合的场景：** 需要复杂路由（按业务线、优先级分发）、请求-响应式的 RPC、
或者团队规模小想快速上手。这些场景下 Kafka 的模型反而碍事——
它没有交换机，路由逻辑得写在生产者和消费者里。
```

`docs/rabbitmq/01-定位与路由.md`：

```text
# RabbitMQ · 定位与路由

RabbitMQ 是实现了 AMQP 0-9-1 的传统消息代理（broker），核心抽象是「交换机 + 队列 + 绑定」。
生产者把消息发给交换机，交换机按 routing key 和绑定规则投递到一个或多个队列。

路由能力是它最强的地方。direct / topic / fanout / headers 四种交换机，
topic 模式支持 `order.*.created` 这样的通配绑定。要做「按业务线分发」「按优先级分发」，
配置几行绑定就行，不需要改代码——这是 Kafka 给不了的。

消息被 ack 之后就从队列删除。它默认是队列，不是日志：不保留历史，不支持重放。
这个差别决定了它和 Kafka 的分工。
```

`docs/rabbitmq/02-投递语义与运维.md`：

```text
# RabbitMQ · 投递语义与运维

投递语义上支持「至少一次」。配合 publisher confirm 和消费者手动 ack 能做到可靠投递，
但「恰好一次」需要业务侧做幂等，别指望 broker 帮你解决。

队列堆积是个需要注意的点。消息在被 ack 前留在内存，堆积量大了会换页到磁盘，
性能明显下降。所以 RabbitMQ 适合「消费能力跟得上生产」的场景，
不适合当缓冲区扛长期堆积——那正是 Kafka 的强项。

运维上单机很容易起步，自带管理界面，可观测性开箱即用。
集群要处理镜像队列或 Quorum 队列的选主问题。Erlang 生态对不熟悉的人有一点门槛，
但日常运维基本碰不到 Erlang 层。

单条消息延迟低，适合 RPC 式的请求-响应和任务分发。吞吐比 Kafka 低一个量级左右，
但它的定位本来也不是大吞吐管道。
```

`docs/rabbitmq/03-适用场景.md`：

```text
# RabbitMQ · 适用场景

**任务队列与工作分发。** 一个任务只被一个 worker 处理，处理完就没了——
这正是队列语义，不需要保留历史。

**复杂路由。** 按业务线、按地区、按优先级分发消息，用 topic 交换机几行配置搞定。
Kafka 做同样的事要写不少代码。

**请求-响应。** 低延迟加上 RPC 风格的调用，适合服务间同步调用解耦。

**中小规模系统。** 单机起步，团队不用专门养一个消息队列运维。

**不适合的场景：** 大吞吐日志管道、需要重放历史、多下游独立消费同一份数据。
这些场景下队列语义会变成负担——消息消费完就没了，第二个下游要读只能重新生产一份。
```

`docs/pulsar/01-架构与多租户.md`：

```text
# Pulsar · 架构与多租户

Pulsar 是 Yahoo 开源的云原生消息平台，走「计算存储分离」路线：
broker 无状态负责收发，存储层 BookKeeper 负责持久化。

broker 无状态意味着扩缩容不用搬数据，加机器就能扛更多连接。
存储层独立扩缩，分层存储可以把冷数据自动卸载到对象存储（S3/OSS），
保留几个月甚至几年的历史而不撑爆本地磁盘。

原生支持租户 / 命名空间 / topic 三级隔离，配配额和鉴权。
多团队共用一套集群时这个设计省事——Kafka 要做同等隔离得自己搭多套集群或者靠 ACL 硬凑。
```

`docs/pulsar/02-消费模型与运维.md`：

```text
# Pulsar · 消费模型与运维

同时支持队列语义（共享订阅，一条消息只被一个消费者处理）和流语义（独占/故障转移订阅）。
同一个 topic 既能当队列用也能当流用，不用改架构——这一点比 Kafka 灵活，
Kafka 要做队列语义得靠消费者组和分区的分配来凑。

吞吐接近 Kafka，单条延迟在低负载时更低，因为 broker 不用等刷盘就能 ack。

运维成本是它最大的短板。组件最多：broker、BookKeeper 的 bookie、元数据存储，
三套东西都要管，端到端链路的排障路径也更长。
社区和生态比 Kafka 小，遇到冷门问题可参考的资料少一些。
托管服务（如 StreamNative）能缓解，但会引入供应商依赖。
```

`docs/pulsar/03-适用场景.md`：

```text
# Pulsar · 适用场景

**多租户平台。** 一个集群服务多个团队，靠命名空间做配额和隔离，
比给每个团队搭一套 Kafka 省事得多。

**长保留与分层存储。** 需要留几个月到几年的历史，又不愿意一直买大盘。
分层存储把冷数据自动挪到对象存储，这个能力 Kafka 要靠 Tiered Storage 插件补，
成熟度不如 Pulsar 原生。

**既要队列又要流。** 同一个 topic 上，实时链路用共享订阅做任务分发，
离线链路用独占订阅做全量消费，互不干扰。

**不适合的场景：** 团队没有相应运维能力、规模不大的项目。
为了用上多租户和分层存储而背上三套组件的运维负担，通常不划算。
```
</details>

### 看一次真实运行

用上面的九份资料和已配置的接口，实际采集到下面这段输出（`multi` 模式，原样保留）。注意三件事。

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

已完成全部流程。以下是选型建议及评审意见。

---

## 选型建议

**推荐**：
- 中小规模、要任务队列/复杂路由/请求-响应、看重低延迟与易运维 → **RabbitMQ**；
- 主打高吞吐日志/事件管道、事件溯源、流式 ETL → **Kafka**；
- 需要多租户隔离、队列+流双语义、长保留分层存储且有专职运维 → **Pulsar**。

**不推荐**：
- 无运维能力的小团队别选 Pulsar（三套组件运维重）；
- 需要消息重放或"一份数据多下游独立消费"时别选 RabbitMQ（消费即删、不支持重放）。

---

## Reviewer 提出的问题

1. RabbitMQ"消费即删、不支持重放"不准确：未确认不删，且可用死信/重发实现重放。
2. RabbitMQ 支持发布/订阅，多下游独立消费可各建队列，故"别选"理由失当。
3. 忽略中小规模也可能需要重放/多订阅，以及无运维团队用 Kafka 也有 KRaft/ZK 压力。
4. 未比较客户端生态、云托管、扩展性、顺序/事务等关键因素。
5. "低延迟/高吞吐"无量化，请求-响应并非 RabbitMQ 独有。
```

**第一，四个子 Agent 全部没做到字数要求。** 提示词里写的是"不超过 150 字"，实际交回来的是 446、256、338、201 字。模型对长度约束的遵守一向松散，多 Agent 系统里这会直接变成上下文膨胀——你以为子 Agent 会帮你压缩，结果它只是搬了个家。

**第二，评审 Agent 读进去 0 字，却挑出了真问题。** 它没有任何工具，只看到主管写的那份建议，就指出"RabbitMQ 消费即删、不支持重放"这个说法不准确。它说得对：RabbitMQ 是 ack 之后才删，而且能用死信队列做变通，原文那句"不支持重放"确实说满了。这就是 Cognition 说的干净上下文——**它没读过那三份资料，所以它不知道"资料里是这么写的"，只按常识判断这话站不站得住。**

**第三，主管的上下文里只剩结论。** 三个研究员各自读了一千字左右，主管拿到的是三段摘要。研究员读过哪些文件、按什么顺序读的、中间有没有犹豫，全都没上来。

## 七、什么时候别用：三张账单

多 Agent 不是免费的。在动手之前，先看看这三张账单。

### 第一张：token 账单

Anthropic 的数据很实在：普通对话里的 Agent 大约用掉聊天 **4 倍**的 token，而多 Agent 系统用掉聊天 **15 倍**的 token。

他们的结论也很实在："For economic viability, multi-agent systems require tasks where the value of the task is high enough to pay for the increased performance."——多 Agent 要求任务本身的价值足够高，高到能付得起这笔溢价。

换句话说：**如果这个任务的产出不值 15 倍的钱，那它就不该用多 Agent。** 用一句"帮我查个函数在哪"去启动一个多 Agent 系统，是纯粹的浪费。

### 第二张：协调账单

Anthropic 早期踩的坑很典型：Agent 会给简单查询生成 **50 个子 Agent**，会无休止地在网上找根本不存在的来源，会互相用频繁的进度更新干扰对方。

他们最后的解法是在提示词里写死规模规则：

- **简单事实查找**：1 个 Agent，3-10 次工具调用
- **直接对比**：2-4 个子 Agent，每个 10-15 次调用
- **复杂调研**：10 个以上子 Agent，职责明确划分

注意这是**写在提示词里的**。模型自己判断不出"这个任务该花多大力气"，你得告诉它。这条经验在任何多 Agent 系统里都适用：**别指望主管 Agent 自己学会控制规模。**

### 第三张：调试账单

单 Agent 已经够难调了，多 Agent 是难度的平方。

Anthropic 的原话是："Agents make dynamic decisions and are non-deterministic between runs, even with identical prompts."——同样的提示词，两次跑出来不一样。他们的例子是用户报告"Agent 找不到明显的信息"，而团队完全看不出为什么：是搜索词不好？是选错了来源？是工具挂了？最后是靠**完整的生产链路追踪**才定位到问题。

Cognition 还补了一刀，关于那些看起来很燃的 demo——20 万行代码的浏览器、10 万行的 C 编译器、优化 LLM 训练脚本：

> 它们都有一个共同点，而大多数真实软件没有：**一个简单、可验证的成功标准**。

浏览器能编译通过、C 编译器能编译 C 代码，这是二元的、可自动判定的。而真实的软件要的是"放大人类的品味和决策"——那是一个完全不同的目标，多 Agent 并行写在这个目标下只会把品味撕成几份。

### 一张判断表

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
