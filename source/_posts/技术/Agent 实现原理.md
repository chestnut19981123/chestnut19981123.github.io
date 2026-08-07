---
title: Agent 实现原理：从一条"修 bug"指令说起
cover: cover.jpg
categories: '技术'
tags: ['AI', 'Agent']
date: 2026-08-07
---

## 开场：它真的去干活了

先说一个场景。某天我打开 Claude Code，顺手丢给它一句话：

> 帮我查一下为什么登录接口 500

说完我就准备切走去看视频了——按我的认知，AI 聊天就是问一句答一句，这种活儿它大概率会回一句「请提供更多信息」，然后礼貌地装死。结果它一声没吭，直接开干。截一段当时的终端（示意输出，非真实日志）：

```text
$ claude
> 帮我查一下为什么登录接口 500

  • 查日志：tail -f /var/log/api.log
    → /api/login 返回 500，抛出 NullPointerException
  • 定位：grep -rn "login" src/main/java/
    → LoginController.java:42
  • 修复：补一行判空
  • 验证：mvn test → 全部通过

✓ 完成：空指针未判空导致 500，已修复并跑通测试
```

它查日志、翻代码、改完还自己跑了测试——全程没问我一句。我坐在旁边，像看同事加班：插不上手，又不好意思走。

回过神来，我发现这事有点反直觉：**这不是一个答案，这是一段行为**。我拿到的不是一句「原因可能是 XXX」，而是一连串动作——查日志、翻代码、改代码、跑测试，一环扣一环。它不是一次性回答，而是**边看边做**：做完一步，看一眼结果，再决定下一步，直到任务完成。

这篇文章想把 Claude Code、Codex 这类工具拆开，看看是什么原理，能让模型从「回答一句话」变成「完成一件事」。官网在 [Claude Code](https://claude.com/claude-code) 和 [Codex](https://openai.com/codex/)，装一个自己试试，比看我写十篇都有用。

> 这类工具的商业实现不开源，但社区有忠实还原其架构的开源实现（MIT 协议）。下面贴的代码都是真实摘录——标注了源文件名，你可以照路径去翻。

## 核心循环：不是一次回答，而是一串行动

先记住全文最核心的一句话：**在 Agent 里，模型的每次响应都不是最终答案，而是下一步行动**。

回看刚才那条修 bug 的任务：它压根不是一次对话，而是一轮接一轮的循环，每轮三步：

1. **推理**：模型看一眼当前的全部上下文（你说的话、之前的操作和结果），决定下一步做什么
2. **执行**：宿主（运行 Agent 的那个进程）按模型的要求调用工具——读文件、跑命令、翻日志，把结果带回来
3. **观察**：工具结果被喂回给模型，进入下一轮推理

用伪代码写出来，就是这样一个循环：

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

把它和普通 LLM 对话放在一起对比，区别一眼就能看出来：

![普通 LLM 对话 vs Agent](fig-vs.svg)

普通对话是一轮即止的问答：你问，它答，然后……没有然后了。聊天机器人会写诗，但不会帮你改 bug——因为它没有手也没有眼睛，改完代码没法跑测试，跑完测试没法看结果。Agent 的不同就在于，问答外面多套了一层循环：**每一步都用真实世界的反馈来校正下一步**。

![Agent 核心循环](fig-loop.svg)

循环总得有个出口，终止条件主要有三个：

- **模型自己判断任务完成**：它不再请求工具，直接给出最终回答，对应伪代码里的 `break`
- **用户叫停**：随时可以按 Ctrl+C，或者直接说「先别弄了」
- **步数或时间上限**：宿主兜底，防止模型在一个任务上跑到天荒地老

### 生产级的代码长什么样

伪代码把骨架画清楚了，但它是「理想模型」——真实实现里，每一行都要应付生产的乱局：网络会抖、模型会抽风、用户会中途按 Ctrl+C。下面贴一段真实实现的主循环节选（`query.py`，和主线无关的细节都用 `...` 省掉了）：

```python
while True:                                              # 外层：Agent 循环本体
    messages = state.messages
    ...
    assistant_messages, tool_use_blocks = await _call_model_sync(
        provider=params.provider,
        messages=messages,
        tools=effective_tools,
        ...
    )

    needs_follow_up = len(tool_use_blocks) > 0           # 有工具请求 → 还要继续

    if not needs_follow_up:                              # 没有 → 任务完成
        set_terminal(holder, natural_termination, Terminal(reason="completed"))
        return

    tool_results = await _run_tools_partitioned(         # 执行所有工具
        tool_use_blocks, params.tool_registry, ...
    )

    state = QueryState(                                  # 重建状态：结果回填进消息
        messages=[
            *messages,            # 原始历史
            *assistant_messages,  # 含 tool_use 的助手回复
            *tool_results,        # 工具结果作为消息回填
        ],
    )
    # 回到 while True，开始下一轮
```

骨架和伪代码一模一样：推理 → 判断要不要继续 → 执行 → 回填 → 下一轮。但凑近了看，差距全在细节里。

**第一处差距：消息不裸传，装在状态对象里。** 伪代码里的 `messages` 是个光秃秃的列表，真实实现里它躺在 `QueryState` 状态对象里（`state.messages`）。而且每轮结束，代码不是原地往里塞消息，而是**重建一个全新的 `QueryState`**：原始历史、助手回复、工具结果三部分拼起来，连同轮数、压缩进度这些元信息一起装进去。每轮一个全新快照，谁也污染不了谁。

**第二处差距：模型调用带保险。** 代码块里那个 `await _call_model_sync(...)`，外面还套着一层被 `...` 藏起来的内层循环——那是重试循环：调用失败、超时、被限流（HTTP 529），就退避重试；你按 Esc 或 Ctrl+C，`abort_signal` 立刻把中止信号传进去，重试循环看到信号就地收手，绝不硬着头皮再撞一次。伪代码里一行 `llm(messages)` 写起来潇洒，生产级实现必须回答「调用失败怎么办」这个问题。

**第三处差距：终止不靠 break，靠显式枚举。** 伪代码退出靠 `break`，真实实现里循环的每个出口，都要先 `set_terminal(...)` 记下**为什么**终止，再 `return`。原因不是随手写的字符串，而是一份固定枚举（`TerminalReason`，一共 11 种）：任务自然干完是 `completed`；轮数到上限是 `max_turns`——对应伪代码里那个「宿主兜底」；你在流式输出时按 Ctrl+C，留下的是 `aborted_streaming`，工具跑到一半被叫停，则是 `aborted_tools`。宿主拿到 `Terminal`，才能分清「干完了」「被叫停」「出岔子了」三种结局，而不是两眼一抹黑。

**第四处差距（也是最关键的一处）：工具结果以消息形式回填。** 看重建 `QueryState` 时拼进去的三样东西：`*messages`、`*assistant_messages`、`*tool_results`——工具结果和助手回复一样，是**一条正经消息**。这守住的是一条不变式：**消息列表永远是模型视角的完整对话**。模型下一轮看到的，不是宿主塞来的一坨「工具输出」，而是按对话顺序排好的完整上下文：自己说过的话、要过的东西、得到的回复，一条不少。这正是「观察」环节的实现——结果不是丢给模型，而是成为对话的一部分，模型才能边看边做。

说起来，这个循环跑起来有点像派了个实习生：你得给它反馈，它才能往下走。区别是这个实习生不会累，也不摸鱼——你喂多少轮结果，它就有多少轮产出。

## 工具调用：只会动嘴的军师

上一节的伪代码里，`response.tool_use` 和 `host.execute(tool)` 两行就把「模型调工具」带过了。但你停下来想想：模型凭什么调用工具？它连文件系统都碰不到——输入是文本，输出也是文本。

所以真相是：**模型从来不会真的「用」工具，它只会「提请求」**。工具调用发生在对话里，而不是模型的身体里——做法是，宿主把可用工具写成 schema 塞进上下文，相当于告诉模型「你手里有这些牌」：

```json
{
  "name": "read_file",
  "description": "读取指定文件的内容",
  "input_schema": {
    "type": "object",
    "properties": {
      "path": { "type": "string", "description": "文件路径" }
    },
    "required": ["path"]
  }
}
```

这段 JSON 的意思是：有个工具叫 `read_file`，给它一个字符串 `path` 就行。于是当它修 bug 修到一半想看源码时，它不会自己动手，而是输出一段结构化的 JSON 请求：

```json
{
  "type": "tool_use",
  "id": "toolu_01ABC",
  "name": "read_file",
  "input": { "path": "src/main.py" }
}
```

注意动作的名字：`tool_use`——是「请求使用」，不是「正在使用」。模型说「我要读 `src/main.py`」，说完就没了，手一步没动。真正动手的是宿主：解析 JSON，记下 id `toolu_01ABC`，真把文件读出来，再把结果回填进对话：

```json
{
  "type": "tool_result",
  "tool_use_id": "toolu_01ABC",
  "content": "def main():\n    print('hello')\n"
}
```

`tool_use_id` 把请求和结果对上号——模型读完，进入下一轮推理。这套「请求 + 回填」结构就是 Claude API 消息格式里工具调用的标准形态；§1 伪代码那两行背后发生的事，到这里也全清楚了。

### 工具到底是什么：一个绑定体

上面这套 JSON 往返，是模型眼里看到的世界。绕到宿主后台看一眼：工具在那儿可不是飘在空中的 schema，而是实打实的一个对象。下面贴一个真实的工具数据结构（`build_tool.py`，和主线无关的字段用 `...` 省掉了）：

```python
@dataclass
class Tool:                                              # build_tool.py
    name: str
    input_schema: Mapping[str, Any]                      # JSON Schema，发给模型
    call: Callable[[dict[str, Any], ToolContext], ToolResult]   # 真正的执行函数
    check_permissions: Callable[[dict[str, Any], ToolContext], PermissionResult]
    is_concurrency_safe: Callable[[dict[str, Any]], bool]
    is_read_only: Callable[[dict[str, Any]], bool]
    ...
```

一眼扫过去，`Tool` 是个普通的数据类，`name`、`input_schema` 俩字段看着眼熟——上一段 JSON 就是从它俩序列化出来的，宿主拿去发给模型当「牌面」。真正干活的都在后面：

- `call`：执行函数，吃进模型给的参数（`dict[str, Any]`）和上下文（`ToolContext`），吐出 `ToolResult`。读文件、跑命令，全在这个回调里。
- `check_permissions`：执行前的权限检查，返回 `PermissionResult`——放行还是拒绝，先过它这一关。
- `is_read_only`、`is_concurrency_safe`：两个标记，一个说「只读」，一个说「并发安全」。宿主靠它们决定工具能不能并行、要不要小心伺候。

**所以一个工具，是「声明 + 执行 + 标注」的绑定体**：给模型看的是 `input_schema`，给机器跑的是 `call`，两个灵魂绑在同一个 `Tool` 对象上，谁也离不开谁——schema 写得再漂亮，没有 `call` 就是空壳；`call` 再能打，模型不知道参数长什么样，也没法正确点菜。

光看抽象类不过瘾，再看一个真实工具的完整定义（`tools/grep.py`——§0 里定位 `LoginController.java:42` 的那把刀，长这样）：

```python
# tools/grep.py —— 一个真实工具的完整定义
GrepTool: Tool = build_tool(
    name="Grep",
    check_permissions=_grep_check_permissions,
    input_schema={
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "pattern": {
                "type": "string",
                "description": "The regular expression pattern to search for in file contents",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in (rg PATH)",
            },
            "output_mode": {
                "type": "string",
                "enum": ["content", "files_with_matches", "count"],
            },
        },
        "required": ["pattern"],
    },
    call=_grep_call,
    description="A powerful search tool built on ripgrep",
    is_read_only=lambda _input: True,
    is_concurrency_safe=lambda _input: True,
)
```

几个值得玩味的细节：

- `required` 里只写了 `pattern`：搜索词必填，`path`、`output_mode` 都可选——不写 `path`，默认在当前目录搜。模型提交的参数必须符合这份 schema，牌面之外的点菜，宿主接不住。
- `is_read_only=lambda _input: True`、`is_concurrency_safe=lambda _input: True`：永远只读、并发安全。Grep 只翻不写，宿主放心让它随便跑，连问都省了。
- `check_permissions=_grep_check_permissions`：权限检查挂在这儿，Grep 有自己的路径检查，§4 再细说。

看一眼这个定义就明白了：**模型手里只有 `input_schema` 的牌面，执行权在 `call` 里，而 `call` 握在宿主手里。** 声明归声明，执行归执行，分得清清楚楚——这正是权限能管住它的前提。

而前面那套 JSON 往返，还压着一条硬约束：**`tool_use` 和 `tool_result` 必须一一配对。** 在宿主内部，一次工具请求就是 `ToolCall`、`ToolResult` 两个对象的事，靠 `tool_use_id` 串在一起：每条 `tool_use` 都带一个 `id`（`toolu_01ABC`），每条 `tool_result` 用 `tool_use_id` 指回去。宿主下次调 API 时，消息列表里任何一条 `tool_use` 都得有对应的 `tool_result`——要是上一轮模型请求了工具，宿主却忘了回填，留下一条没人认领的孤儿 `tool_use`，下一次调用直接 400：消息格式不合法，对话当场断掉。

这就解释了 §1 那句「工具结果以消息形式回填」为什么是硬要求：不回填，下一轮根本走不下去。消息必须成对出现，不是协议设计者的洁癖，是这套机制的地基。

**记住这一节最关键的一点：模型只提请求、不碰执行权。** 它输出的从头到尾都是 JSON 文本；读文件、跑命令、改代码这些有副作用的动作，全攥在宿主手里。这让权限控制第一次变得可能：宿主能在执行前拦下请求，问用户「允许 / 询问 / 拒绝」。模型的「手」长在宿主身上，而宿主听谁的，是可以配置的——权限是安全性的核心，后面单独开一节细说。

![工具调用的往返](fig-toolcall.svg)

这张图把一次往返画全了：左边模型只动嘴，右边宿主才动手。那句「得嘞，内容给您」，就是 `tool_result` 回填时宿主的内心独白——它等这份内容，等得还挺认真。

最后留个坑：各家 Agent 的工具协议并不统一，各写各的 JSON。MCP 想当那个通用的「USB 接口」，统一协议、即插即用。这个也值得单独写一篇。

## 上下文管理：鱼的记忆

工具调用解决了「怎么动手」，但还有个更隐蔽的问题：**模型记不住那么多事**。

模型没有硬盘，它的全部工作记忆就是那个上下文窗口。§1 说过，每一轮「推理 → 执行 → 观察」都会把新的往返塞进窗口——修 bug 这种任务几十轮下来，窗口肉眼可见地膨胀，而它的大小是有上限的。都说金鱼的记忆只有七秒，模型也好不到哪去：让它连续干两个小时活，你会发现它开始忘事——不是它傻，是窗口就那么大。

于是长任务靠三条策略续命：

**截断。** 窗口快满时，把最早的消息直接丢掉，给新内容腾地方。实现最简单，代价也最直白：丢掉的多半是任务的开始——那句「帮我查一下为什么登录接口 500」可能还在，但你随口说过的项目背景、约束条件，全没了。模型带着残缺的记忆继续干活。

**压缩。** 把聊过的内容总结成一段摘要，用摘要换空间。Claude Code 的 auto-compact 就是这种思路的公开行为：对话太长时，自动把前面的内容压成摘要再继续。细节会丢，主线还在——就像期末复习：笔记太长，删掉重抄一遍精华。

**落盘记忆。** 还有一类信息根本不属于「这一轮对话」，而是长期重要的：构建命令、代码风格、你的偏好。这些不该放在窗口里等被挤掉，而是写进 CLAUDE.md / memory 文件，每次任务开始时重新读一遍。**写下来比记住更可靠。**

![上下文窗口：鱼的记忆](fig-context.svg)

图里把两种结局并排画了出来：左边窗口塞满红了，右边压缩一下又活了。底部那行才是重点——重要的长期信息别放窗口里，写进文件里。

顺带一提 prompt caching：系统提示、工具定义这些每一轮都一样的内容，其实不用每次从头算——相同前缀的 token 直接复用缓存结果，省时间也省钱。

## 安全与权限：不会开火的实习生

§2 结尾说，权限是安全性的核心，要单独开一节细说——现在来兑现。§2 里讲过，模型只有建议权，它输出的全是 JSON 请求，动手的永远是宿主。那问题自然就来了：**宿主凭什么听它的？** 万一它哪轮脑子一热，请求「删掉整个数据库」，宿主也得照办？

当然不。宿主在动手之前，先过三道闸门：

- **允许**：这工具早就在放行名单里，直接执行，连问都不问
- **询问**：拿不准，弹窗问用户——§1 伪代码里那行「可能触发权限确认」的注释，说的就是这一下
- **拒绝**：拦下请求，把「被拒」的结果回填给模型。注意模型不会原地崩溃，它收到一条拒绝，自己换条路接着走

Claude Code 的权限模式、Codex 的 approval 机制，各家长相不同，拆开看都是这三态的排列组合。于是整个模型就像个**没有开火权限的实习生**：查日志、翻代码随便来，真要执行有副作用的操作，一律先走审批流。反过来，你把权限模式切到 auto，等于把公章直接交给它——审批全免、效率拉满，可万一闯了祸，背锅的也是你。

三态之外还有一层兜底：**沙箱**。文件系统只让读写指定目录，网络走代理、受限，命令有白名单有黑名单——把 Agent 关进指定的笼子，就算它真起了坏心思也出不去。这也顺带解释了工具为什么必须设计得「窄而明确」：`read_file`、跑一条命令，边界清清楚楚；「随便执行任何 Python」这种宽工具就危险了，你根本没法预判它会被拿去干嘛。

最后留个钩子：有的宿主还允许在循环的固定时点挂 hooks，每次工具调用前或后插一段自定义检查。原理不复杂，但能做的不少，值得单独开一篇。

## 收尾：一条指令的完整旅程

把这几节串回开头那条修 bug 的指令，完整旅程长这样：指令进门，核心循环驱动它一轮接一轮地转；动手靠工具往返——模型动嘴、宿主动手；记性靠窗口管理——截断、压缩、落盘，保证不忘事；安全靠权限护航——三道闸门加沙箱，保证不乱来。四个模块环环相扣，「一句话」就这么变成了「一件事」。

每个模块往里挖都还有得写：上下文压缩具体怎么压、工具协议各家怎么设计、MCP 想怎么统一、hooks 能玩出什么花。后面我会不定期更新，把它们拆开细讲。你最想看哪块，评论区说一声，我优先写它。

最后回到开头那句话：它是真的去干活了。原理你知道了，下次要不要也丢给它一句话试试？
