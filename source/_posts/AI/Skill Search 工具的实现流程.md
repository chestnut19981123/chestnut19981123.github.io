---
title: Skill Search 工具的实现流程：从 TF-IDF 到三个接入面
cover: cover.png
categories: 'AI'
tags: ['AI', 'Agent', '工具']
date: 2026-08-20
---

## 开场：模型不知道它有什么牌

先讲一个每天都在发生的尴尬场景。Agent 里的 skill 越攒越多——`browser-playwright`、`git-commit-helper`、`code-review`、`sop-converter`……一坨又一坨。但你有没有想过一个问题：**skill 多了，模型真的知道它们存在吗？**

它不知道。模型不是搜索引擎，它看到的 skill 列表里夹着三十个 SKILL.md 的标题和简介，翻了半天也没搞明白哪个能派上用场。就像你衣柜里堆了八十件衣服，早上出门时能想起来的永远是那三件——剩下七十七件不是不好看，是你根本不知道它们挂在哪儿。

那怎么办？办法很朴素：**给 Agent 装一个搜索工具**。让它遇到问题先搜一把：「我要干浏览器自动化，有没有对应的 skill？」——一个工具，把 skill 从「躺在仓库里」变成「随叫随到」。

这篇文章就以 Skill Search 工具为例，完整拆一遍一个工具的实现流程。从核心的分词、TF-IDF 算法，到外围的三个接入面——它怎么被 Agent 用、怎么在 CLI 里被调、怎么变成斜杠命令。这三条线是**最日常的三个入口**，你会发现它们最后殊途同归，汇进同一条管道。

> 本文代码全部摘自其开源仓库，标注了源文件路径，可以照路翻。想看原版的朋友欢迎去 [GitCode](https://gitcode.com/Ascend/AgentSDK) 围观。

## 一、核心功能：TF-IDF 是怎么算出来的

先看它最硬核的部分：给定一个自然语言查询，怎么在几十个 skill 里找到最相关的那个。答案分三步：**文档化 → 分词 → 打分**。

### 从 Skill 到文档：一次无痛瘦身

Skill 模型本身是个大胖子，三十多个字段：名字、显示名、描述、正文、`when_to_use`、`allowed_tools`、来源、隐藏标记……搜索不需要这么多。所以第一步，把它压缩成一个 8 字段的搜索文档：

![从 Skill 到搜索文档](fig-extract.svg)

几个值得注意的设计决策：

**描述从哪来？** `_extract_description` 优先取 `when_to_use`（什么时候该用它）而不是 `description`——因为前者是语义最丰富的字段，直接描述适用场景，搜索时最有用：

```python
def _extract_description(skill: "Skill") -> str:
    """Extract the searchable description.

    Priority: ``when_to_use`` > ``description`` > empty string.
    """
    when = skill.when_to_use
    if when:
        return when
    return skill.description or ""
```

> 作者注：为什么 `when_to_use` 比 `description` 更值得搜？想想 SKILL.md 是怎么写出来的——`description` 是给目录页看的，作者多少端着；`when_to_use` 回答的是「什么场景该想起我」，作者会掏心窝子。搜索搜的是意图，当然挑掏心窝子的那段读。

**标签从哪来？** Skill 模型根本没有 `tags` 字段，那就硬造：从 `allowed_tools`（比如 `["bash", "python"]`）、名字里的命名空间（`browser:playwright` → `["browser", "playwright"]`）、来源（`userSettings`）三个地方拼出来。注释里写得很诚实：「等哪天 SKILL.md 加了 tags 字段，直接读就行」——**先用着，将来再说**，这就是工程。

**文档 ID 怎么生成？** `make_id` 用 SHA-256 对 `"source:name"` 哈希取前 16 位。这样同一个来源 + 同一个名字，无论在哪个进程、哪台机器上算，ID 都一样——索引可以落盘、加载、增量更新而不会对不上号。

还有一套 **来源权重**：`project` 权重 1.3、`local` 1.1、`template` 1.0、`mcp` 0.9。项目里的 skill 最贴近当前工作，权重最高；MCP 来的泛用工具权重最低。打分时乘上去，让「本地项目经验」压过「通用工具」。

### 分词：一个能换引擎的分词器

接下来是分词。这里有个设计很漂亮：**没有一门语言被硬编码**。所有语言逻辑都收敛在 `LangProcessor` 抽象基类里，想支持新语言，写个类插进去就行：

```python
class LangProcessor(ABC):
    """Language-aware tokenizer for a specific script or character range."""

    @abstractmethod
    def can_handle(self, char: str) -> bool:
        """This processor handles this character?"""

    @abstractmethod
    def tokenize_segment(self, segment: str) -> list[str]:
        """Split a pure-script segment into tokens."""

    @property
    def priority(self) -> int:
        return 100        # 数字越小优先级越高
```

每个处理器管一段字符范围，靠 `priority` 排优先级。内置了三个：

- **LatinProcessor**（priority 10）：管英文和数字。它能拆 camelCase——`BrowserPlaywright` 被正则拆成 `Browser` + `Playwright`；还能拆大写缩写——`XMLParser` 拆成 `XML` + `Parser`；大小写折叠 + 停用词过滤（`the`、`and`、`how` 这类词直接扔掉）。
- **CJKProcessor**（priority 20）：管中日韩。中文没有空格分词，默认用**字符二元组**（bigram）：`"浏览器"` 变成 `"浏览"` + `"览器"`。如果装了 jieba，就升级成词级分词——`create_default_tokenizer` 的 `cjk_word_tokenizer="auto"` 参数会尝试 `import jieba`，装了就 `jieba.lcut`，没装就退回 bigram（有 jieba 吃大餐，没 jieba 吃泡面，反正饿不死）。
- **FallbackProcessor**（priority 9999）：兜底。西里尔字母、泰文、阿拉伯文……谁都不认识的字，它把每个字符单独保留。**保证数据不丢**——搜不到是算法问题，丢数据是事故。

分词主流程 `Tokenizer.tokenize` 四步走：

![分词管线](fig-tokenize.svg)

```python
def tokenize(self, text: str) -> list[str]:
    segments = self._segment_text(text)          # 1. 扫描全文，按处理器分片
    tokens: list[str] = []
    for processor, segment in segments:
        tokens.extend(processor.tokenize_segment(segment))  # 2. 各片分词
    tokens = self._normalize(tokens)             # 3. 长度过滤（1~64 字符）
    if self._deduplicate:
        tokens = self._deduplicate_keep_order(tokens)  # 4. 去重保序
    return tokens
```

`_segment_text` 从第一个字符开始，找它归属的处理器，然后把后面所有同处理器字符归成一段，一路扫到尾。一段「浏览器 automation」被切成「浏览器」片 + 「automation」片，分别喂给 CJK 和 Latin。**同一个查询，两套引擎各干各的，互不干扰**——多语言支持，就该是这个样子。

### TF-IDF 索引：五张表 + 一条公式

分词只是把文本变成 token 列表，真正算分的在 `TfIdfSkillIndex`。它内部维护五张数据结构：

![TF-IDF 索引结构](fig-index.svg)

```python
@dataclass
class TfIdfSkillIndex:
    tokenizer: Tokenizer
    config: SkillSearchConfig
    doc_store: dict[str, SkillSearchDocument]     # doc_id → 原始文档
    token_counts: dict[str, int]                  # doc_id → 总 token 数（长度归一用）
    inverted_index: dict[str, list[tuple[str, int]]]  # term → [(doc_id, 词频)]
    doc_freq: dict[str, int]                      # term → 多少文档含它
    idf: dict[str, float]                         # term → 预计算的 idf
    total_docs: int = 0
```

经典倒排索引结构：`inverted_index` 记「哪个词出现在哪些文档里、各几次」，`doc_freq` 记「词有多稀有」，`idf` 是预计算好的稀有度分数。搜索时只要查表相加，不用扫全库。

打分公式长这样（`index.py` 的模块注释）：

```
score(doc, query) = doc.weight × Σ_{term ∈ query} [
    (tf(term, doc) / √total_tokens(doc)) × idf(term)² × field_boost
]
```

四个因子，逐个拆：

- **`tf / √total_tokens`**：词频归一化。一个词在文档里出现 3 次比 1 次相关，但长文档天然词频高，除以总 token 数的平方根拉平。这是标准的 **length normalization**——不然每篇 skill 都写两千字长文，谁字多谁赢，那叫水文比赛。
- **`idf(term)²`**：稀有词加权。`idf = log((N+1)/(df+1)) + 1`（平滑 IDF，加 1 保证恒正），**再平方**——让罕见的词权重更高。搜「playwright」时，所有 skill 里只有两篇提过这个词，这个信号就该比「browser」这种烂大街的词值钱。（打个比方：在广场上喊「喂」，全街回头；喊你的名字，只有认识你的人回头——越冷门的声音，指向越明确。）
- **`field_boost`**：字段加权。名字和标题里命中 = 3.0，标签 = 2.5，描述 = 2.0，正文 = 1.0。一个词出现在 skill 名字里，显然比深埋在正文某段里更说明问题。实现上很鸡贼：**索引时就把 boost 烘进词频里**——`_tokenize_and_count` 按字段分词，`name` 里出现的词计 3 次，`body` 里计 1 次，打分时一个字都不用改。
- **`doc.weight`**：就是前面说的来源权重（project 1.3 / local 1.1 / …）。乘在最外层。

搜完按分数降序排，`min_score` 过滤掉低于阈值的噪声，`top_k` 截断（默认 8 个）。每个结果还带上 `matched_terms` 和一行人类可读的 `reason`——`matched "browser", "playwright"`——模型拿到的不是「第 3 个结果」，而是「为什么是它」。

**索引的增删改**也值得一说。`build()` 全量重建；`upsert()` 增量更新（先 `remove` 旧的再插新的，最后 `_recompute_all_idf()` 全表重算）；`remove()` 把倒排索引里的引用删干净，词频递减到 0 的 term 连根拔起。注意这里的「增量」边界：`doc_store`、`token_counts`、`total_docs` 按文档增删，`inverted_index` 和 `doc_freq` 只动被改文档涉及的词条——唯独 `idf` 没法按文档增量维护，它的公式里带着全局文档数 N，每增删一篇，全词汇表每个词的 `idf` 都要按新 N 重算。好在重算成本只随词表大小走——八千多个词，一次重算毫秒级——值得。

**持久化**走原子写：先写 `.tmp` 文件，再 `os.replace` 换名覆盖。这保证磁盘上要么是旧版本、要么是完整新版本，**永远不会读到写一半的烂文件**。加载时检查格式版本号，对不上直接抛 `IndexCorruptError`。

### 上层封装：SkillSearcher 与勤快的 watcher

索引是裸引擎，`SkillSearcher` 是点着火、能上路的那台：

- **`ensure_index()`**：懒加载。优先从磁盘 `load`；文件缺失或损坏就 `refresh()`——从注册表全量重建再存盘。**坏了不怕，重造一个就是**。
- **`search()`**：pinned（置顶）的 skill 永远排前面，再按 `tags` / `source` 事后过滤。
- **`pin() / unpin()`**：把高频 skill 钉在顶上，`pinned.json` 持久化。
- **`inspect() / stats()`**：看某个 skill 的逐字段 token 拆分，或索引统计——调优时的放大镜。

最后是 `SkillIndexWatcher`，一个勤快的小工。skill 注册是动态的——用户随时可能往技能文件夹里丢一个新 skill。watcher 监听注册表事件，来了新 skill 就增量 `upsert` 进内存索引，**不必全量重建**。为了避免频繁写盘，保存做了 5 秒冷却：连续注册十个 skill，只写一次盘。全程 `threading.Lock` 保护，注册在哪个线程都不怕。

到这里，搜索引擎本体完工。但注意：它现在还只是一堆类和几个函数，**没有任何入口让模型碰到它**。接下来的三章，就是给这台发动机装三个方向盘——三个接入面。

## 二、接入 Tool System——给 Agent 的手

第一个接入面，是让 **Agent（模型）** 能用手去摸它。这是最核心的一章，因为前面文章已经讲过：模型本身是「只会动嘴的军师」，它要碰任何东西，都得通过宿主准备好的工具。Skill Search 想被模型用，就得先成为工具。

### Tool System 的基础架构

先说这个系统本身长什么样。之前贴过 `Tool` 这个数据类的骨架，这次看它的完整身份：

```python
@dataclass
class Tool:
    name: str
    input_schema: Mapping[str, Any]                      # 给模型看的"牌面"
    call: Callable[[dict[str, Any], ToolContext], ToolResult]  # 真正的执行函数
    prompt: Callable[..., str]                           # 教模型怎么用
    description: Callable[[dict[str, Any]], str]
    check_permissions: Callable[[dict[str, Any], ToolContext], PermissionResult]
    is_enabled: Callable[[], bool]
    is_concurrency_safe: Callable[[dict[str, Any]], bool]
    is_read_only: Callable[[dict[str, Any]], bool]
    is_destructive: Callable[[dict[str, Any]], bool]
    to_auto_classifier_input: Callable[[dict[str, Any]], Any]
    aliases: tuple[str, ...] = ()
    search_hint: str | None = None
    ...
```

![Tool 绑定体](fig-tool.svg)

老规矩：**一个工具是「声明 + 执行 + 标注」的绑定体**。`input_schema` 序列化成 JSON 发给模型当牌面；`call` 是模型点菜后真正掌勺的；剩下的全是标注——`is_read_only` 说「这工具只读，放心并发」、`is_destructive` 说「这工具会删东西，小心伺候」、`check_permissions` 说「跑之前先过我这关」。

工具太多了，手写 30 个字段太累，所以有个 `build_tool()` 工厂函数：传字符串的 `prompt` / `description` 自动包成函数，没传的字段用 `TOOL_DEFAULTS` 兜底（默认非只读、默认不并发、默认放行权限）。

工具们住进 `ToolRegistry`。它是注册表 + 分发器二合一：

- **`register()`**：名字大小写不敏感，重名直接报错，别名（`aliases`）一并登记。注册失败会回滚——不会留下半注册的脏状态。
- **`dispatch()`**：真正执行的地方，也是一条 **统一通路**。任何入口——模型、CLI、斜杠命令——最终都走它。流程是：

```python
def dispatch(self, call: ToolCall, context: ToolContext) -> ToolResult:
    tool = resolve_tool_for_context(context, call.name, base_registry=self)
    if tool is None:
        return ToolResult(name=call.name, output={"error": f"unknown tool: {call.name}"}, is_error=True, ...)

    context.ensure_tool_allowed(tool.name)
    coerced_input = validate_tool_input(tool.name, call.input, tool.input_schema)  # 语义强转
    if context.plan_mode and tool.name in _DESTRUCTIVE_TOOLS:                       # 计划模式防御
        ...
    if tool.validate_input is not None:                                            # 自定义校验
        ...
    decision = has_permissions_to_use_tool(tool, call.input, context.permission_context, ...)  # 权限
    if decision.behavior == "deny":
        return ToolResult(..., is_error=True)
    if decision.behavior == "ask":                                                 # 弹窗问用户
        ...
    result = _invoke_tool_call(tool, call.input, context)                          # 执行
    return result
```

`validate_tool_input` 做语义强转——模型传来 `"true"`（字符串）会被转成 `True`（布尔）；权限层分 `allow` / `deny` / `ask` 三态，`ask` 时弹窗问用户；plan 模式下对写文件的工具直接拒绝。**所有工具共用这一套安检**，新工具零成本获得权限系统、校验系统、并发控制——像机场安检，头等舱、经济舱过的是同一道闸机，谁也别想插队。

### 接入：两步，把 SkillSearch 送进模型的工具池

把搜索引擎装进这个系统，一共两步：**定义工具**，然后**登记进注册表**。

**第一步：定义工具。** 整个定义就在 `tools/skill_search.py` 一个文件里，核心是最后这几十行：

```python
# tools/skill_search.py —— 一个真实工具的完整定义
SkillSearchTool: Tool = build_tool(
    name="SkillSearch",
    input_schema={
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["search", "pin", "unpin", "inspect", "rebuild", "stats"],
                "description": "Action to perform: search (find relevant skills), "
                               "pin/unpin (manage pinned skills), inspect (show token "
                               "breakdown), rebuild (force index rebuild), stats (index statistics)",
            },
            "query": {"type": "string", "description": 'Natural language description. E.g., "browser automation". Required for search.'},
            "name":  {"type": "string", "description": "Skill name. Required for pin, unpin, inspect."},
            "top_k": {"type": "integer", "description": "Max results (default: 8). Only for search."},
            "tags":  {"type": "array", "items": {"type": "string"}, "description": "Filter by tags. Only for search."},
            "source": {"type": "string", "enum": ["local", "project", "mcp", "template"], "description": "Filter by source. Only for search."},
        },
        "required": ["action"],
    },
    call=_skill_search_call,
    prompt=SKILL_SEARCH_TOOL_PROMPT,
    description="Search for relevant skills, manage pinned skills, and inspect skill index",
    is_read_only=lambda _input: _input.get("action") not in ("pin", "unpin", "rebuild"),
    is_concurrency_safe=lambda _input: False,
    search_hint="skill search find relevant skills tfidf discover",
    to_auto_classifier_input=lambda _input: _input.get("query", ""),
)
```

一个工具，六个动作：`search` / `pin` / `unpin` / `inspect` / `rebuild` / `stats`。这个设计挺有意思——把「一个工具」当成「一个小型 API 的入口」，用 `action` 字段区分功能。好处是模型只需要记住一个名字；坏处也在这里：schema 里的 `query` / `name` 等参数是不同 action 共用的，描述里得不断声明「仅 search 用」——像药品说明书上那句「忌与酒同服」，印在每一粒药丸上。

工具文件里装三样东西：工具定义、`call` 指向的薄壳、背后的进程级单例。`_skill_search_call` 已经薄成壳了：取 `action`、交出去、包回结果，五行完事：

```python
def _skill_search_call(input_data: dict[str, Any], context: ToolContext) -> ToolResult:
    from services.skill_search.actions import run_action

    action = input_data.get("action", "search")
    result = run_action(action, input_data)
    return ToolResult(name="SkillSearch", output=result.text, is_error=result.is_error)
```

真正的动作 handler（每个都很薄，比如 search 就是拿 query 调 `searcher.search()` 再把结果排成文本）和它背后的**进程级懒加载单例** `get_searcher()` 一起住在 services 层，为所有接入面共用：

```python
# services/skill_search/actions.py
def get_searcher():
    """Lazily create and cache the process-wide SkillSearcher singleton."""
    from extensions.skills_ext.registry_ext import get_default_registry
    from services.skill_search.config import SkillSearchConfig
    from services.skill_search.searcher import SkillSearcher
    from services.skill_search.tokenizer import create_default_tokenizer

    searcher: SkillSearcher | None = getattr(get_searcher, "_instance", None)
    if searcher is None:
        config = SkillSearchConfig.from_feature_gate()      # 从 feature gate 读开关
        registry = get_default_registry()
        tokenizer = create_default_tokenizer(cjk_word_tokenizer=None)
        searcher = SkillSearcher(registry, config=config, tokenizer=tokenizer)
        get_searcher._instance = searcher                   # 挂在函数属性上
        if config.enabled:                                  # 开着才启动 watcher
            searcher.create_watcher().start()
    return searcher
```

注意三个细节：**单例挂在函数自己的 `_instance` 属性上**，不污染全局命名空间；`create_default_tokenizer(cjk_word_tokenizer=None)` 关闭 jieba——工具场景要快，bigram 足够；watcher 只在 feature gate 开着时才启动——注意这个判断发生在**第一次真正调用**时（模块导入不执行），而且省的是后台：无线程、无回调、不写盘。严格说开关一关，第一次调用仍会构造出 searcher 对象，随后才报「没开」——省的不是对象图，是 watcher 的后台活动。甚至工具本身还在模型的工具池里，gate 只管索引和 watcher，不管工具在不在场。

**第二步：登记进注册表。** 工具文件写好了，还要让系统知道它存在：

![从定义到模型](fig-agent.svg)

`tools/__init__.py` 维护着 53 个核心工具的名单 `ALL_STATIC_TOOLS`——在里面加一行 `SkillSearchTool`，`build_default_registry()` 启动时遍历名单逐个 `registry.register()`（这是 Stage A 同步阶段；Stage B 的扩展工具延迟到后台线程注册，省 3 秒冷启动）。之后每次对话组装工具池 `assemble_tool_pool()` 时自动带上它——内置工具排前面、MCP 工具排后面，不是美观问题，**内置工具块是 prompt cache 的断点**，MCP 工具增增减减不能让它前面的缓存失效。

就这两步。**完成标准**：模型侧零改动——宿主会自动把每个工具的 `input_schema` 序列化进上下文 → 模型决定用哪个 → 输出一段 `tool_use` JSON → 宿主拿它构造 `ToolCall` → `registry.dispatch()` 执行 → 结果回填对话。SkillSearch 的 schema 进上下文后，模型「不知道有什么 skill」的问题就解决了：**它可以先搜一把，再决定用哪个**。

## 三、接入 CLI——给操作者的手

第二个接入面，是让 **人** 在终端里直接调它。没有模型，不需要 REPL，一条命令敲下去工具就执行。它的做法很聪明：**不给你准备专用命令，而是把「调任意工具」本身做成了通用命令**。

### CLI 的基础架构

CLI 的骨架是三层：`main.py` 入口 → `dispatch.run_cli()` 分发 → `subcommand_registry` 注册表。注册表用装饰器注册：

```python
# subcommand_registry.py
_SUBCOMMANDS: dict[str, SubcommandHandler] = {}

def register(name: str) -> Callable[[SubcommandHandler], SubcommandHandler]:
    """Register a fast-path subcommand handler."""
    def decorator(handler: SubcommandHandler) -> SubcommandHandler:
        _SUBCOMMANDS[name] = handler
        return handler
    return decorator
```

各子命令模块（`provider_cmd`、`model_cmd`、`stats_cmd`……）在 `load_builtin_subcommands()` 里被延迟导入——导入的**副作用**就是把 `@register("xxx")` 都登记上。这个「导入即注册」的模式让新增子命令只需写一个模块 + 一个装饰器。

骨架到此为止——它只回答 argv 怎么路由到子命令。工具怎么进 CLI？总不能给每个工具都写一个 `skill-search` 子命令吧——argparse 不支持通配子命令，导入期全量注册又违背「零配置」原则。于是 `tool_cmd/` 模块给出了答案：**只注册一个 `tool` 子命令，第一个参数是工具名，其余参数转发**：

```text
tool SkillSearch --action search --query "browser automation"
t SkillSearch --action search --query "browser automation"   # 短别名
tool --list                                                  # 列出可调用的工具
tool SkillSearch --help                                      # 查看某个工具的用法
```

实现分三段，每段都有讲究：

**第一段：构造独立环境。** CLI 是独立进程，不共享 REPL 的内存，所以 `_build_tool_registry()` 现造一个默认注册表；`_build_tool_context()` 造一个 ToolContext，权限模式设为 `bypassPermissions`——操作者都敲了 `tool <name>` 了，等于声明「这工具的副作用我认了」。工作目录设为 `$PWD`，这样 Read/Write 类工具按操作者的当前目录解析路径。

> 作者注：`bypassPermissions` 听着吓人，其实只对人肉调用生效——命令都亲手敲出来了，再弹一次权限确认框纯属多此一举。模型走的是另一条道，该问的照问，不耽误。

**第二段：JSON Schema → argparse。** `schema_parser.build_arg_parser()` 把工具的 `input_schema` 编译成 `argparse` 解析器——`query` 字段变成 `--query` 参数，`enum` 变成 `choices`，`required` 变成必填。**工具定义一次，命令行参数自动生成**，零手写——schema 写对了，参数表自己长出来。

**第三段：复用同一条通路。** 解析出的参数包成 `ToolCall`，直接丢进 `registry.dispatch()`——和模型调用走的是**同一个函数**，校验、权限、执行，一点不差。唯一的差别是 bypass 权限模式，以及 `core_filter` 会拦下核心工具（Bash、Read、Write 这些），防止你把核心系统工具当子命令乱调——不过 SkillSearch 在白名单上：它只读、无副作用，拦截的理由（权限旁路）对它不成立。

![CLI 分发流程](fig-cli.svg)

### 接入：给核心工具签一行白名单

新增 SkillSearch 后，CLI 侧只改一处：

**第一步：白名单登记。** SkillSearch 撞上了 `core_filter` 的拦截——它是**核心工具**（模型专用），Bash、Read 那些放命令行被乱调可不行。放行方式是手工登记一行：

```python
# core_filter.py —— 核心工具的白名单，人工维护，不是自动判定
CLI_EXPOSED_CORE_TOOLS: frozenset[str] = frozenset({"SkillSearch"})
```

非核心工具则直接跳过这一步——注册进 `ToolRegistry` 后 `tool <名字>` 自动可用，零适配，通用命令的价值就体现在这儿。

**完成标准**：`tool SkillSearch --help` 能看到从 schema 自动生成的参数表；再敲一个真实动作验证：

```text
tool SkillSearch --action stats
Skill Search Index Stats
=======================
  Documents:     53
  Unique terms:  8303
  Inverted size: 22351 entries
  Approx memory: 117874 bytes
  Pinned skills: 1
    test-skill
```

## 四、接入斜杠命令——给 REPL 的手

第三个接入面：在交互式 REPL 里，敲 `/` 开头的命令。和前两个接入面不同，这个入口是**手工铺设**的——在 `builtins.py` 里手写一个 `LocalCommand` 注册进去。

### 斜杠命令的基础架构

命令系统四个部件：`LocalCommand`（命令定义）、`CommandRegistry`（注册表）、`CommandEngine`（执行引擎）、`parse_user_input`（输入解析）。

命令本体是一个 `LocalCommand`，名字 + 描述 + 用法提示，外加 `set_call()` 绑定处理函数：

```python
SKILLS_COMMAND = LocalCommand(
    name="skills",
    description="List available skills or search/reload the skill index",
    argument_hint="[search <query> | inspect <name> | pin <name> | unpin <name> | rebuild | stats]",
    supports_non_interactive=True,
)
...
SKILLS_COMMAND.set_call(skills_command_call)
```

执行引擎 `CommandEngine.execute` 干的事很朴素：输入必须以 `/` 开头 → 空格切出命令名和参数 → `registry.get()` 找命令 → 按类型分发（`LOCAL` 直接调 call，`PROMPT` 走提示词，`INTERACTIVE` 走交互流程）→ 跑完触发命令钩子。入口侧的 `parse_user_input` 负责把用户输入归类：`/xxx` 开头是命令、`\/xxx` 是转义文本、`@file` 是文件提及……分类决定输入走命令管道还是对话管道。

这套骨架的细节到此为止——它只是把「`/xxx` 字符串」翻译成「命令名 + 参数」再分发的管道；本章真正的主角是下面这条接入路径：手工的 `/skills` 怎么把六个 action 直接送到 services 层。

### 接入：手工铺设的 `/skills`

接入是三步，一步一步来。

**第一步：定义。** `builtins.py` 里定义 `SKILLS_COMMAND`——名字、描述、用法提示，就是上面「基础架构」那段的代码块。

**第二步：绑定。** `set_call()` 把处理函数挂到命令上——`skills_command_call` 按子命令分发：`search` / `inspect` / `pin` / `unpin` / `rebuild` / `stats`，无参数时列出全部 skill 并附上索引统计，顺手告诉用户「用 /skills search 找」：

```python
def _skills_subcommand(args: str) -> LocalCommandResult:
    parts = args.split(maxsplit=1)
    sub = parts[0].lower()
    rest = parts[1] if len(parts) > 1 else ""
    if sub == "search":
        params = {"query": rest}
    elif sub in ("pin", "unpin", "inspect"):
        params = {"name": rest}
    else:
        params = {}
    result = run_action(sub, params)  # ← 和工具是同一条分发
    return LocalCommandResult(type="text", value=result.text)
```

**第三步：登记。** 把 `SKILLS_COMMAND` 加进 builtins 的命令列表，装载时统一 `registry.register()`，和其他十几个命令一起上场。手工命令不用进 `ALL_STATIC_TOOLS`，也不用白名单——命令系统不认识工具系统，`builtins.py` 就是它唯一的家。

**完成标准**：在 REPL 里敲下去就能用：

```text
> /skills search browser automation
Search results for "browser automation":

1. agent-browser  (score: 8.782, source: local)
   Headless browser automation CLI optimized for AI agents with accessibility tree snapshots and ref-based element selection
   matched "automation", "browser"

2. find-skills-skill  (score: 1.028, source: local)
   Search and discover OpenClaw skills from various sources. ...
   matched "automation"
...
```

`/skills` 和 `SkillSearch` 工具共用同一个 `run_action()`、同一个进程级单例——两边入口都只是薄壳：`/skills` 把字符串包成 dict、结果包成 `LocalCommandResult`；工具侧把 dict 原样交出去、结果包成 `ToolResult`。

## 收尾：三条路，同一个终点

回头看这张地图，三章其实画的是同一件事：

![三线汇聚](fig-three.svg)

- **Agent 用**：schema 进上下文，模型输出 `tool_use` JSON → `ToolCall` → `dispatch`
- **CLI 用**：`tool SkillSearch --action search ...` → argparse 解析 → `ToolCall` → `dispatch`
- **REPL 用**：`/skills search ...` → 命令引擎 → `run_action` 直达 services 层

前两条汇进 `ToolRegistry.dispatch()` 这条统一通路——校验、权限、执行，一套代码管两头；入口当然不止这三个——headless、远程 API、orchestrator 自动化等场景同样汇入这条通路；文章挑的，是**最日常的三个**。这就是「接入」的本质：**你只需要把工具声明一次**（写一个 `Tool` 对象、塞进注册表），剩下的 Agent、CLI，全系统自动帮你接好。手工的 `/skills` 是唯一的例外——它不走闸机，从 builtins 直达 `run_action`，跳过工具层的校验与权限，换来聚合 UX。代价也明摆着：它只在本地 REPL 出现，因为只有这儿，敲命令的人就是工具的使用者本人。

三个接入面，动作清单一目了然：

| 接入面 | 你要做的 | 完成标准 |
|---|---|---|
| **Agent** | `tools/skill_search.py` 定义 `SkillSearchTool`；`ALL_STATIC_TOOLS` 加一行 | 模型对话里能搜到 skill 并调用 |
| **CLI** | 非核心工具零配置；核心工具在 `CLI_EXPOSED_CORE_TOOLS` 登记一行 | `tool SkillSearch --help` 出参数表 |
| **REPL** | `builtins.py` 定义 `LocalCommand`；`set_call`；加进命令列表 | `/skills search ...` 出结果 |

所以下次你给 Agent 写新工具时，记住这个配方：**核心算法自成服务（services 层），薄薄一个 `build_tool` 把它包成工具（tools 层），塞进 `ALL_STATIC_TOOLS`，注册表接管一切**。Agent 和 CLI 两张方向盘自动装好，你只管点火；REPL 那边想要斜杠命令，就得自己动手写一个 `/skills` 挂上去——哦对了，只读的核心工具想上 CLI，还得在白名单上签个名（`CLI_EXPOSED_CORE_TOOLS`）。
