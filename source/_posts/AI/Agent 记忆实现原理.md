---
title: Agent 记忆实现原理：窗口、会话与仓库
categories: 'AI'
tags: ['AI', 'Agent', '记忆', 'OpenCode']
date: 2026-11-10
cover: cover.svg
description: 拆解 Agent 的记忆机制——窗口里的压缩、SQLite 里的 checkpoint、AGENTS.md 的重新注入；压缩是视图，不是删除，长期记忆不是被摘要继承的，而是被重新注入的。
---

## 开场：重启之后，它还记得

为了写这篇，我实际跑了一个小实验。临时目录里放两个文件：

```text
AGENTS.md
hello.txt
```

`AGENTS.md` 里写两条约定：每次回复必须以 `BANANA-42` 开头；如果被问到项目代号，回答 `ORCHID-7`。`hello.txt` 里只有一行 `hello from the demo project`。

用一个临时项目、两个假代号，是为了让「记住」这件事可验证：如果它答出 `ORCHID-7`，只可能来自 `AGENTS.md`，不可能来自模型的世界知识。

然后用 OpenCode 2.2.5 让它读 `hello.txt`。它读完，回复的第一行是 `BANANA-42`，第二行是文件内容。接着我触发一次压缩，把前面的对话压成摘要。摘要里没有 `BANANA-42`，也没有 `ORCHID-7`——它只记了「用户让助手读 `hello.txt`，任务完成」。

最后，我问它：「项目代号是什么？」

它回答：

```text
BANANA-42

ORCHID-7
```

窗口里的原始对话已经被压掉了，摘要里也没有这条约定，它凭什么还记得？答案不是「模型记性好」。压缩完成后，宿主把 `AGENTS.md` 从磁盘重新读了一遍，又塞回了上下文。

这个小实验把本文要讲的三种记忆都串起来了：

- **工作记忆**：窗口里那段对话。它会被压缩，压缩后的视图比原文小。
- **会话记忆**：SQLite 里的消息和 checkpoint。原始消息没删，压缩只是换了模型看到的那一份。
- **项目记忆**：仓库里的 `AGENTS.md`。它不进摘要，每次由指令加载器重新注入。

一句话概括：**压缩是视图，不是删除；长期记忆不是被摘要继承的，而是被重新注入的。** 再补一句更准确的说法：**视图里只放指针，原文只在会话库里留一份。**

这篇只拆 OpenCode 2.2.5（tag `v2.2.5`，commit `9bbb8ce`）。它开源、压缩实现完整、`AGENTS.md` 的发现和重注入都能在源码里逐行对上，适合拿来当解剖样本。另一家怎么做，收尾一句带过。

## 总览：三种寿命

先把「记忆」这个词拆开。本文的定义很窄：**能被重新读进上下文的东西，才算记忆。** 存在磁盘上但永远不会再被读回来的日志，不算；模型 weights 里那些说不清道不明的「知识」，也不算。

按这个定义，OpenCode 的记忆有三种寿命，分别放在三个可见的载体里：

| 记忆类型 | 载体 | 寿命 | 写入者 | 读取时机 | 失效方式 |
|---|---|---|---|---|---|
| 工作记忆 | 上下文窗口 | 秒 / 分钟 | 模型与宿主 | 每次请求 | 压缩、溢出、窗口关闭 |
| 会话记忆 | SQLite（`opencode.db`） | 小时 / 天 | 宿主 | resume、加载历史 | 删除会话、库损坏 |
| 项目记忆 | `AGENTS.md` | 周 / 月 | 人 | 会话启动、压缩后重注入 | 文件改动、删除、路径变化 |

![三种记忆的寿命](fig-three-layers.svg)

这张表里最值得多看一眼的是「写入者」和「失效方式」。三种记忆不是同一套东西换三个名字：写的人不同，坏的方式也不同。窗口的问题是「太多」，所以它靠压缩；会话的问题是「断了」，所以它靠落库和 checkpoint；项目记忆的问题是「过时」，所以它靠每次重读，而不是把内容抄进摘要。

把三种记忆分开，不是为了凑三层，而是因为它们回答三个不同的问题：这一轮模型现在能看到什么（窗口）；进程崩了之后，这一轮还能不能接上（会话库）；换一个会话、换一天，项目约定还在不在（`AGENTS.md`）。三个答案不能互相替代：窗口再大，也不保证崩溃后能恢复；会话库再全，也不会自动把项目约定塞进新会话。

还有一个容易被误解的点：OpenCode 没有「Agent 自写的个人记忆库」。它的长期记忆是显式的——人写 `AGENTS.md`，系统写会话库。模型不能偷偷往某个隐藏档案里记一笔，下次再翻出来。这个设计不一定更强，但它足够透明，适合拆。

第二个误解是「记忆等于检索」。这套记忆里没有向量库，也没有相似度搜索：会话按 `seq` 顺序加载，`AGENTS.md` 按目录关系发现后整份读入。它不判断「哪段历史跟当前问题最像」，只判断「哪些东西属于当前会话、当前项目」。这也是它和 RAG 的分界：RAG 检索外部的、相对静态的知识，解决「不知道去哪找」；这里的记忆跟踪会话和项目的状态，解决「刚才发生了什么」。前者可以每次重建索引，后者必须保留时间顺序。

## 工作记忆：窗口里的预算与压缩

窗口是模型唯一能直接看到的地方。系统提示词、工具定义、指令文件、对话历史、工具结果、给回复预留的空间，全挤在这里。它们不是白来的，每一段都占 token。

![窗口预算](fig-budget.svg)

### 预算：先给回复留座位

压缩的触发阈值不是「窗口的 80%」，而是一个减法（源码是 TypeScript + Effect；以下代码都是节选，省略了类型标注和生成器外壳，`yield*` 只出现在源码的 generator 里）：

```ts
const RESERVE_MIN = 16_000
const RESERVE_SHARE = 0.15
const UNKNOWN_WINDOW = 200_000

const calculateCeiling = (limit, buffer) => {
  const window = inputWindow(limit)
  if (window <= 0) return Number.POSITIVE_INFINITY
  // ...buffer 的显式覆盖分支略
  return window - Math.max(
    Math.floor(window * RESERVE_SHARE),
    window >= 2 * RESERVE_MIN ? RESERVE_MIN : 0,
  )
}
```

`inputWindow` 取模型声明的输入上限和上下文窗口的较小值。剩下的部分再减去一个「预留」：通常是窗口的 15%；如果窗口至少 32k，就至少留 16k。`max` 而不是 `min` 是有意的：小窗口按比例留，大窗口至少留 16k；两者取较大值，保证预留不会因为窗口变大而被比例稀释。换句话说，压缩不是在窗口塞满时才发生，而是在窗口还剩一段余量时就发生。

为什么留余量？因为压缩请求本身也要输出。摘要不是白写的，它要占生成空间；压缩完成后的下一轮对话也要空间。如果等到 100% 再压，摘要还没写完，请求就先被 provider 拒了。`SUMMARY_OUTPUT_FLOOR = 32_000` 就是给摘要输出留的下限：宁可多留，不要在门槛上摔跤。

窗口大小未知时，`calculateCeiling` 返回无穷大，自动压缩不会触发——不知道天花板在哪，就不要假装知道。但真要压缩时，请求会按 `UNKNOWN_WINDOW = 200_000` 估算一个尺寸。这是两件事：**自动触发要保守，手动压缩要有个可用的默认值。**

### 触发：实测加估算，越过天花板

有了天花板，下一步是判断「现在到底用了多少」。OpenCode 不数消息条数，也不只信估算，它把两者加起来：

```ts
const due = (context, ceiling, estimate) => {
  const messages = context.messages
  const last = messages.at(-1)
  if (last?.type === "compaction" && last.status === "completed") return false
  const measured = messages.findLastIndex((m) => hasMeasuredPrompt(m, context.model.ref))
  if (measured < messages.findLastIndex(SessionHistory.isNativeCompaction)) return false
  return total(estimate ?? estimatePrompt(context)) >= ceiling
}
```

`hasMeasuredPrompt` 找的是最近一次带真实 token 计数的 assistant 消息。provider 返回的 `usage` 是实测值，比本地估算准；但它只覆盖到那一次请求。之后新增的消息还没被 provider 数过，只能用估算补上。`total = measured + estimated`，两者相加，再和 ceiling 比。

这个设计解决了一个很实际的问题：token 估算会漂。中文、代码、工具结果、图片，每一种的估算误差都不一样。只信估算，可能提前压，也可能压晚了；只信实测，又只能知道上一次请求的大小，新消息全在盲区。实测锚点加后续估算，是在「准」和「新」之间折中。

还有一个细节：如果最后一条消息是刚完成的 compaction，`due` 直接返回 false。为什么？因为 runner 还没根据新的 checkpoint 重建请求，这时候再压一次，等于拿旧视图重复劳动。

### 保留：最后 15k 原文

压缩不是把整个对话都换成摘要。默认保留最近 `keep = 15_000` token 的原文，和摘要一起送给模型。保留哪一段，由 `splitConversation` 和 `recentStart` 决定：

```ts
const splitConversation = (messages, keep) => {
  const entries = messages.flatMap((message) => {
    const text = SessionRecentText.messageToText(message)
    return text ? [{ message, text }] : []
  })
  if (entries.length === 0) return undefined
  const first = entries[recentStart(entries, keep, previousCompaction(messages))]
  return { keepID: first?.message.id }
}
```

`recentStart` 从最新一条往前数，丢掉最旧的，直到剩下的估算 token 不超过 `keep`；然后从丢弃边界附近找一个 user 消息作为起点。这个「找 user 边界」的动作很关键：assistant 的一次工具调用和它的结果不能被拆开。如果起点落在 assistant 的 tool call 上，保留的尾部就会有一个没有结果的调用，模型看到会懵。

保留最近原文的理由很朴素：摘要有损。越早的对话，越可能只留下「做了什么」的结论；越近的对话，越可能包含「下一步具体怎么改」的细节。下一步最可能用到的，是最近这几轮。

### 摘要：七段模板与文件指针

摘要由一次单独的模型调用生成，提示词里有一个固定模板。模板要求七段：

- `Objective`：用户想完成什么
- `Requirements`：用户说过的约束、偏好、范围
- `Decisions`：已经做过的决定和理由
- `Work State`：分成 `Completed`、`Active`、`Blocked`
- `Next Move`：下一步动作，按顺序
- `Relevant Files`：最多 15 条，只写路径和「为什么重要」
- `Important Context`：下一个 Agent 不知道就没法继续、又不容易自己查到的信息

七段里最容易被低估的是 `Work State`。它把工作分成 `Completed`、`Active`、`Blocked` 三态，而不是一句「做到哪了」。`Blocked` 尤其重要：它逼摘要写清楚「卡在哪、等什么」，下一个 Agent 才不会把时间浪费在重复尝试上。`Next Move` 则要求按顺序写，避免下一个 Agent 面对一堆并列建议，不知道先做哪个。

![七段摘要](fig-summary.svg)

`Relevant Files` 是整张模板里最像「指针」的部分。它不要求把文件内容抄进来，只要求路径和理由。路径比内容稳定：内容会变，路径不会天天变；下一个 Agent 需要细节时，可以自己打开文件。`SUMMARY_RULES` 把这条原则写得很直白：

> Prefer short references over detailed restatement. It is fine to leave out information the next agent can recover from the code or the files listed above.
>
> 优先写短引用，不要详细复述。下一个 Agent 能从代码或上面列出的文件里恢复的信息，可以省略。

最多 15 条，是给摘要的硬上限：文件列得越多，每条的理由就越短，指针反而变糊。

同一段规则还要求保留精确的文件路径、符号、命令、错误字符串、URL 和标识符。这看起来矛盾——既要短，又要精确——其实不矛盾：**短的是叙述，精确的是指针。** 「我改了登录接口」是叙述，「`LoginController.java:42` 的 `login()` 补了判空」是指针。后者更短，也更有用。

### 预计算：提前写，但先不换

写摘要是一次完整的模型调用，可能要几十秒。如果等到触发那一刻才开始写，用户会明显感到卡顿。OpenCode 有一个预计算机制：上下文到 ceiling 的 85%、且实测 token 至少 64k 时，后台先把「最新响应之前」的历史总结掉。

```ts
const PRECOMPUTE_RATIO = 0.85
const PRECOMPUTE_MIN_TOKENS = 64_000
const PRECOMPUTE_MAX_FAILURES = 2

const precompute = (load, given) => {
  const settings = state.get()
  if (!settings.precompute || !settings.auto) return
  // ...
  if (total(estimate) < ceiling * PRECOMPUTE_RATIO) return
  const anchorIndex = context.messages.findLastIndex((m) => hasMeasuredPrompt(m, context.model.ref))
  const anchor = context.messages[anchorIndex]
  if (anchorIndex <= 0 || anchor?.type !== "assistant" || !anchor.tokens) return
  if (anchor.tokens.input + anchor.tokens.cache.read + anchor.tokens.cache.write < PRECOMPUTE_MIN_TOKENS) return
  // ...
}
```

注意第一行：**预计算默认是关的**（`precompute: false`）。它是个可选优化，不是默认行为。打开之后，它也不是「提前压缩」，而是「提前写好摘要，先攥在手里」。真正触发压缩时，如果这份摘要还能用，就直接换上；如果它已经落后太多，就丢掉重写。

为什么不提前换？因为换摘要会改写请求的前缀。provider 的提示词缓存是按前缀命中的，前缀一变，缓存全废。预计算的价值在于「写」可以提前，「换」必须等到该换的时候。这个分寸感，是整套机制里最像工程而不是像算法的地方。

短会话摸不到这两道门槛，默认关闭不影响它们；预计算优化的是长会话的尾延迟，代价是可能白写一次摘要——会话在触发压缩前结束，这份摘要就用不上了。

### 溢出：从截断到只留用户文本

再周全的预算也会遇到意外：provider 报 `too long`。这时候 OpenCode 不直接失败，而是按四级比例收缩，重试：

```ts
const SHRINK_STEPS = [0.85, 0.7, 0.5, 0.35]
const TRANSCRIPT_LEVELS = [0, OUTPUTS_CLIPPED, OUTPUTS_REMOVED, USER_ONLY, OMITTED]
const TRANSCRIPT_CLIP = 2_000
const TOOL_OUTPUT_MAX_CHARS = 1_250
```

`SHRINK_STEPS` 是每次重试的目标比例：以上一次被拒的请求大小为基准，分别缩到 85%、70%、50%、35%。`TRANSCRIPT_LEVELS` 是摘要 transcript 的缩短级别：完整；截断工具输出；去掉工具输出并截断工具输入；只留用户文本；整段省略。`TRANSCRIPT_CLIP = 2_000` 是截断时保留的首尾字符数。

保留的最近消息也有裁剪：工具输出最多 `TOOL_OUTPUT_MAX_CHARS = 1_250` 字符，推理内容直接丢弃，附件只留 mime 和文件名，不读字节。这些规则在 `recent-text.ts` 里，目的只有一个：让「最近的原文」在预算内尽量保留信息密度，而不是把一大段 JSON 原样塞回去。

图片按 1,500 token 估，PDF 按 2,000 token 估。估算不可能完美，所以才有上面的重试阶梯。先算，算不准就缩，缩不动就再缩——这套思路不优雅，但很抗造。

## 会话记忆：压缩是视图，不是删除

窗口里的压缩讲完了，现在把视角从「模型看到什么」切到「磁盘上存了什么」。这两个视角必须分开，否则很容易把「压缩」误解成「删除」。

### 存储视图：一条 compaction 消息

OpenCode 的会话存在 SQLite 里，一条消息一行。用户消息、assistant 回复、工具调用、工具结果、synthetic 指令、compaction，都有自己的记录。session 还有 `parentID`，可以派生子会话；子会话有自己的消息，父会话不会替它保存。

压缩完成时，库里多出一条 `compaction` 消息。它不是「把旧消息删掉」，而是一条新的记录，带着摘要和几个元数据：

- `status: "completed"`
- `reason: "manual"` 或自动触发的原因
- `summary`：七段摘要的正文
- `metadata.keepID`：保留的最近消息从哪一条开始

模型下一轮看到的上下文，是这样一个组合：

```text
<conversation-checkpoint>
  <summary>七段摘要</summary>
  <recent-context>keepID 之后的原文</recent-context>
</conversation-checkpoint>
[新消息 ...]
```

而磁盘上的原始消息，一条都没少。

为什么用 SQLite，而不是把会话写成一堆 JSON 文件？因为这里需要事务：消息、compaction、claim、`instruction_state` 要在一个库里一致地更新；也需要并发：多个会话、多个进程可能同时读写。JSON 文件也能用，但锁、崩溃一致性、部分写入都得自己补。OpenCode 选 SQLite，是把它当会话的事实来源，而不是当缓存。

压缩结果也不单独建表，而是作为一条 `compaction` 消息插进同一条消息序列。这不是图省事：`keepID` 引用的是「从某条消息到 compaction」这段区间，如果 compaction 不在序列里，区间就没有右端点。`seq` 给所有消息一个全序，`keepID` 才有确切含义——它指向的不是时间戳，也不是快照，而是全序里的一个位置。

![压缩前后](fig-checkpoint.svg)

### 引用：keepID 与 recent-context

`keepID` 是一个消息 ID，不是一段复制出来的文本。历史加载时，`withRecentText` 拿着这个 ID 回库里查，把 `keepID` 到 compaction 之间的消息读出来，拼成 `recent-context`：

```ts
const withRecentText = (db, sessionID, entries) => {
  const first = entries[0]
  const compaction = first?.message
  if (compaction?.type !== "compaction" || compaction.status !== "completed") return entries
  const keepID = compaction.metadata?.keepID
  if (!Schema.is(SessionMessage.ID)(keepID)) return entries
  const start = yield* db.select({ seq: SessionMessageTable.seq })
    .from(SessionMessageTable)
    .where(and(eq(SessionMessageTable.session_id, sessionID), eq(SessionMessageTable.id, keepID)))
    .get()
  // ...读出 start.seq 到 compaction.seq 之间的消息，拼成 recent
}
```

源码注释把这件事说得很清楚：

> A summary compaction references its kept messages by `metadata.keepID` instead of storing them, so history rebuilds their text from the messages between that one and the compaction, in memory only.
>
> 摘要式压缩用 `metadata.keepID` 引用保留下来的消息，而不是把它们存进摘要；历史加载时，才从那条消息到 compaction 之间的记录里，在内存中重建文本。

这就是「视图存指针，原文只存一份」在会话库里的具体体现。摘要不复制最近消息的原文，只存一个 ID；原文还在消息表里。复制会膨胀，也会过期——同一段对话存两份，改了一处，另一处就成了旧版本。引用没有这个问题：原文只有一份，视图每次现拼。

为什么不删原文？四个理由：审计、回放、重新压缩、导出。删了原文，你就没法回答「它当时到底看到了什么」，也没法在换了模型之后重新压一遍。`transfer.ts` 的导出/导入还要把整个会话带走；原文没了，导出的就只是一份摘要，不是会话。

引用也有代价。如果 `keepID` 指向的消息被删了，`withRecentText` 找不到起点，就会原样返回：最近原文静默消失，既不报错，也不会去别处找副本，因为根本没有副本。这是「只存一份」的另一面——省掉了复制带来的过期问题，也失去了副本带来的冗余。

### 恢复：claim 是一张未完成的欠条

会话记忆还有一半是「断了之后怎么接回来」。OpenCode 用一张 write-ahead 的欠条：`claim`。

```ts
claim: (sessionID) => db.update(SessionTable)
  .set({ time_suspended: Date.now(), time_updated: sql`${SessionTable.time_updated}` })
  .where(and(eq(SessionTable.id, sessionID), isNull(SessionTable.time_suspended)))
  .run(),

release: (sessionID) => db.update(SessionTable)
  .set({ time_suspended: null, resume_attempts: 0, time_updated: sql`${SessionTable.time_updated}` })
  .where(eq(SessionTable.id, sessionID))
  .run(),
```

`claim` 在开始执行一轮时把 `time_suspended` 设成当前时间；`release` 在正常结束时清空它，并把 `resume_attempts` 归零。如果进程崩溃，`time_suspended` 会留在库里；下次启动看到它，就知道「上一轮没跑完」。`countResume` 再给 `resume_attempts` 加一，记录这条会话被恢复过几次。

这解决的是一类很讨厌的问题：模型已经决定调用一个会改文件的工具，工具也执行了一半，进程挂了。重启后如果直接重跑，可能重复写入；如果直接放弃，文件可能停在半改状态。claim 不能自动修好文件，但它至少让宿主知道「这一轮是半截的」，从而选择恢复、回滚或询问用户，而不是装作什么都没发生。

OpenCode 的会话还可以导出和导入。`transfer.ts` 的 `export` / `import` 支持 `sanitize`：导出前可以把敏感的工具状态洗掉。这让会话可以带走、分享、存档，也再次说明原文不是「压缩完就没用了」的临时数据。

## 项目记忆：AGENTS.md 的发现与重注入

工作记忆和会话记忆都是「系统写的」；项目记忆不一样，它是人写的。`AGENTS.md` 里放的是仓库约定、命令、代码风格、注意事项——那些每次开工都该知道、但不该被摘要「继承」的东西。

### 发现：全局、祖先目录与配置

OpenCode 找 `AGENTS.md` 的范围有三块：

1. **全局**：全局配置目录下的 `AGENTS.md`，对所有项目生效。
2. **祖先目录**：从当前工作目录往上走，直到项目根，每一级的 `AGENTS.md` 都收。
3. **配置**：`instructions` 里写的 glob 或 URL，可以额外挂文件，也可以挂远程文档。

源码里的候选列表是这么拼的：

```ts
const candidates = [
  ...(discovery.global ? [globalFile] : []),
  ...(project
    ? ancestorDirectories(start, stop)
        .map((directory) => join(directory, "AGENTS.md"))
        .filter((file) => discovery.global || file !== globalFile)
    : []),
]
for (const file of new Set(candidates)) {
  const updates = yield* watcher.subscribe({ path: file, type: "file" })
  yield* updates.pipe(Stream.runForEach(publish), Effect.forkScoped({ startImmediately: true }))
}
```

`ancestorDirectories(start, stop)` 从 cwd 一路走到项目根。`new Set` 去重，防止全局文件和祖先目录撞车。每个候选文件都挂一个 watcher；文件改了，变化会发布出去。这样 `AGENTS.md` 不是「启动时读一次就完事」，而是持续被监听的。

三段来源按「全局 → 祖先 → 配置」的顺序拼成一条 synthetic 消息，不是覆盖关系：后读到的文件不会让前面的失效，它们的正文直接首尾相接。`load` 里还有一个进程内的 in-flight claim，防止同一路径在并发读取时被注入两次；这个 claim 只在内存里，读完就释放，真正的持久账本仍然是 synthetic 消息的 metadata。

读取失败还分两种。文件在扫描和读取之间消失（可能是编辑器正在保存），`projectSource` 会把整组指令标成 `unavailable`，等下一次刷新重试——它不会拿读到的那几份凑数。文件被拒绝访问（比如在沙箱权限之外），就当作不存在，静默跳过，因为重试也不会变好。一个瞬态、一个永久，处理方式正好相反。

### 注入：一条 synthetic 消息

找到文件之后，OpenCode 把内容读出来，拼成一条 synthetic 消息：

```text
Instructions from: /path/to/AGENTS.md
<文件内容>
```

多个文件就用空行拼在一起。这条消息带一个 metadata：

```json
{ "instruction": { "paths": ["/path/to/AGENTS.md"] } }
```

`synthetic` 是一种特殊的消息类型：它对模型可见，但不是用户说的，也不是 assistant 说的。用 synthetic 而不是偷偷塞进 system prompt，有三个好处：模型能看到、审计能查到、去重能靠 metadata。`previouslyInjected` 会扫描当前可见历史里的 synthetic 消息，把 `instruction.paths` 收集起来，已经注入过的路径不再重复注入。

### 重注入：压缩之后，再读一遍

现在到了全文最关键的一处。压缩之后，旧的 synthetic 消息掉出了模型可见历史。`previouslyInjected` 只扫描「最新 compaction 之后」的 synthetic 消息，所以它看不到旧的注入记录了。于是，指令加载器认为这些文件「还没注入」，重新从磁盘读一遍，再发一条新的 synthetic。

源码里这段注释值得原样抄下来：

> The synthetic message metadata scanned below is the only lasting ledger, so paths whose synthetics drop out of model-visible history (compaction, revert) are re-discovered and re-injected instead of staying silently lost.
>
> 下面扫描的 synthetic 消息 metadata 是唯一持久的账本；因此，那些 synthetic 已经掉出模型可见历史的路径（压缩、revert），会被重新发现、重新注入，而不是悄悄丢失。

这句话解释了小实验里的 `ORCHID-7` 是怎么回来的。但还有一个问题没回答：为什么摘要不直接把 `AGENTS.md` 抄进去，省得再读一遍？

因为摘要提示词明确要求**不要**抄。`buildPrompt` 里有一段：

> Summarize only what the user and the assistant said and did. Leave out instructions and setup the assistant was given rather than told by the user: repository conventions, instruction files such as AGENTS.md, and environment details like the session ID. The next agent receives current versions of all of these separately.
>
> 只总结用户和助手说过、做过的事。不要写进助手收到的、而非用户说出的指令和设定：仓库约定、AGENTS.md 这类指令文件、会话 ID 这类环境信息。下一个 Agent 会单独收到这些东西的最新版本。

这段话是整套设计的题眼。摘要只负责「对话里发生了什么」，不负责「项目约定是什么」。项目约定由另一条通路负责：每次重新读最新版。两条通路各管各的，谁也不抄谁。

抄进摘要有什么坏处？三个：会过时（文件改了，摘要还是旧的）、会重复（摘要一份，注入一份，窗口里两份）、会挤占（约定越长，摘要越臃肿）。重新注入没有这些问题：文件永远是磁盘上的最新版，注入的份额独立计算，摘要也能保持短小。

![AGENTS.md 的发现与重注入](fig-instructions.svg)

## 交接：三种记忆之间怎么搬运

三种记忆不是三个孤岛，它们之间有明确的搬运路径。把路径画出来，整套机制就清楚了。

### 三条通路：写、读、重读

**第一条：窗口 → 会话库（写）。** 每一轮消息都落库。用户消息、assistant 回复、工具调用、工具结果，都有对应的记录。压缩时再写一条 compaction 消息，带上摘要和 `keepID`。这条通路的写入者是宿主，不是模型；模型只负责生成内容，落库是 runner 的事。

**第二条：会话库 → 窗口（读）。** 恢复会话时，`SessionHistory.load` 从库里读出最新 compaction 之后的消息，把 checkpoint 拼成一条 user 消息，再把新消息接在后面。`keepID` 指向的最近原文，由 `withRecentText` 在内存里重建。这条通路的关键是「按需读」：不是把所有历史一次性倒进窗口，而是只读 checkpoint 和它之后的增量。

**第三条：仓库 → 窗口（重读）。** 指令加载器发现 `AGENTS.md`，读内容，发 synthetic 消息。压缩或 revert 让旧的 synthetic 掉出可见历史后，加载器重新发现、重新读取、重新注入。这条通路的关键是「每次读最新版」：不缓存内容，只缓存路径；不复制进摘要，只重新注入。

![一次完整流转](fig-lifecycle.svg)

三种记忆的失败模式可以并排放：

| 记忆 | 谁写 | 谁读 | 坏了会怎样 | 怎么修 |
|---|---|---|---|---|
| 工作记忆 | 模型 + 宿主 | 每轮请求 | 忘了最近的细节 | 压缩，保留最近原文 |
| 会话记忆 | 宿主 | resume、加载历史 | 接不上，或重复执行 | checkpoint、claim |
| 项目记忆 | 人 | 启动、压缩后 | 约定失效，模型瞎猜 | 重读文件 |

三种失效方式对应三种修复，但修复的前提是原文还在。

### 一条原则：视图存指针，原文只存一份

三条通路可以压成一条原则：**视图存指针，原文只存一份；按需取，取完验。**

- 摘要的 `Relevant Files` 存路径，不存文件内容。
- checkpoint 的 `keepID` 存消息 ID，不存最近消息的副本。
- `AGENTS.md` 的注入记录存路径，内容每次从磁盘重读。
- 会话库是唯一保存完整原文的地方；视图（摘要、checkpoint、注入消息）都是它的派生。

这条原则也解释了三种记忆的失效方式为什么不同。窗口失效，是因为视图太大，压小就行；会话失效，是因为连接断了，claim 和 checkpoint 能接回来；项目记忆失效，是因为文件变了，重读就行。三种问题，三种解法，但底层的动作是同一个：**别把原文复制到视图里，视图只留能找到原文的线索。**

## 实测：一次压缩与恢复

前面讲的是源码。这一节讲我真跑的那一次。环境是 OpenCode `v2.2.5`（tag `v2.2.5`，commit `9bbb8ce`），模型 `deepseek/deepseek-flash`，数据目录用 `XDG_*` 环境变量隔离到临时路径，避免碰本机已有的会话库。

### 准备：一个会忘事的实验

临时项目里只有三个文件：

```text
AGENTS.md
hello.txt
notes.md
```

`AGENTS.md` 的内容：

```text
# Demo conventions

- Every reply must begin with the exact token `BANANA-42`.
- When asked for the project code name, answer `ORCHID-7`.
```

第一轮，我让它读 `hello.txt`。它调用 read 工具，回复：

```text
BANANA-42

hello from the demo project
```

这说明 `AGENTS.md` 在会话开始时已经被注入，模型看到了那两条约定。

### 压缩：模型压不了，宿主才能压

我先试着把 `/compact` 当普通消息发给它。它的回复很有意思：

```text
I can't compact the conversation myself — compaction is triggered by the
harness, not by a tool I have access to.
```

这不是模型在推脱，而是事实：压缩是宿主的动作，不是模型能调用的工具。`/compact` 在 CLI 的 `run` 模式里没有被当成命令解析，所以它作为一条普通用户消息进了对话，模型只能如实回答「我压不了」。

真正的入口是本地 server 的接口：

```text
POST /api/session/:sessionID/compact
```

本地 server 用 Basic Auth 保护：用户名固定是 `opencode`，密码在 server 启动时打印。压缩接口是异步的——调用之后，它先返回一条 compaction 记录，摘要由后台模型生成；我轮询会话消息，直到 `status` 变成 `completed` 才继续。这时库里多了一条 `compaction` 消息：

```text
type: compaction
status: completed
reason: manual
metadata.keepID: msg_1c4671389001fnx1YfFs7PSKgU
```

`keepID` 指向的是那条 `/compact` 用户消息，也就是压缩时保留的最近原文的起点。摘要正文是七段模板，节选如下：

```text
## Objective
- User asked the assistant to read `hello.txt` and reply with its exact contents; that task is done.

## Work State
### Completed
- Read `/tmp/oc-demo/project/hello.txt` and replied with its exact contents.

## Relevant Files
- `hello.txt`: contains the single line `hello from the demo project`

## Important Context
- (none)
```

注意两点。第一，`Relevant Files` 只写了路径和理由，没有把文件内容抄进来。第二，`Important Context` 是 `(none)`，摘要里没有 `BANANA-42`，也没有 `ORCHID-7`。这不是摘要漏了，而是提示词明确要求它不要写 `AGENTS.md` 的内容。

### 恢复：它还记得那个代号

压缩完成后，我在同一个会话里问：

```text
What is the project code name? Reply with just the code name.
```

它回答：

```text
BANANA-42

ORCHID-7
```

这回答不可能来自摘要——摘要里根本没有这两个词。它来自压缩后重新注入的 `AGENTS.md`。库里的 `instruction_state` 也留下了痕迹：这条会话的 `epoch_start` 是 35，而 compaction 的 `seq` 是 33；`core/instructions` 的哈希指向 `instruction_blob` 里那份 `AGENTS.md` 的内容。换句话说，压缩之后，指令状态重新建立了一次，文件被重新读进来了。

原始消息也还在。`hello.txt` 那一轮的用户消息、assistant 回复、工具调用、工具结果，一条都没删；`keepID` 只是给视图指了个起点。压缩前后的消息序列大致是：

```text
seq 5    user      读 hello.txt
seq 6    assistant tool call + 回复
seq 15   assistant 最终回复
seq 20   idle      成功
seq 23   user      /compact
seq 24   assistant "我压不了"
seq 29   idle      成功
seq 33   compaction 摘要 + keepID
seq 39   user      问项目代号
seq 40   assistant BANANA-42 / ORCHID-7
```

### 边界：这不是 benchmark

这次实测只跑了一个模型、一个会话、一次压缩。摘要质量会随模型变化，`keepID` 落在哪条消息也取决于当时的对话形状。它能证明机制存在、能按源码描述工作，但不能证明「所有模型、所有会话都会这样」。

还有一个版本细节：npm 上的 `opencode-ai` 没有 2.2.5（最新是 1.19.5）。我用的是 GitHub release 的 Linux x64 二进制，下载后对了 SHA256。如果你要复现，认 tag `v2.2.5` 和 commit `9bbb8ce`，别拿本机旧的 1.x 跑完再引用 2.2.5 的常量——两边的压缩实现不一样。

## 收尾：记忆是视图管理

回到开头那个实验。它之所以能在压缩后答出 `ORCHID-7`，不是因为模型记住了，而是因为三件事同时成立：

- 摘要只记对话，不记项目约定，所以 `AGENTS.md` 没有被摘要「继承」；
- 压缩只改模型视图，不删会话库里的原文，所以历史还在；
- 指令加载器发现旧的注入掉出了可见历史，于是从磁盘重读最新版，重新注入。

三种记忆，三种寿命，三个写入者：

- 工作记忆由模型和宿主共同写，活几分钟，靠压缩管理；
- 会话记忆由宿主写，活几小时到几天，靠 checkpoint 和 claim 管理；
- 项目记忆由人写，活几周到几个月，靠重新注入管理。

它们的失效方式也不同：窗口怕满，会话怕断，项目记忆怕旧。对应的解法分别是压缩、恢复、重读。看起来是三套机制，其实是一条原则：**视图存指针，原文只存一份；该取的时候取，取完确认它还是最新的。**

有的产品把长期记忆做成一个隐藏的个人档案，模型自己往里写，用户看不见；OpenCode 选择把它留在仓库和会话库里，让人能看见、能改、能删。两种路线各有取舍，但后者至少有一个好处：当它答出 `ORCHID-7` 的时候，你能顺着 `AGENTS.md` 找到答案是从哪来的。

压缩不是把过去删掉，而是换一种看法。长期记忆不是被摘要继承的，而是每次重新读进来的。
