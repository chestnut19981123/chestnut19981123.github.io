---
title: LLM API 使用说明书：从一行 curl 到一句人话
cover: cover.svg
categories: 'AI'
tags: ['AI', 'LLM', 'API']
date: 2026-09-09
---

## 开场：它不是智能，是个接口

先破一个泡泡：你天天跟 AI 聊天，以为屏幕对面坐着一个无所不知的智慧体。其实对面更像一家不太会寒暄、但账算得极清楚的外卖窗口。你每敲一句话，背后发生的是一件特别朴素的事——你的机器往某个域名发了一个 POST 请求，请求体是一段 JSON，顺手附上一把 API Key 当入场券。服务器那边不做别的：收下 JSON，算出一个字，回给你，收钱。如此往复，直到它觉得该闭嘴。

这篇文章要做的，就是把这件事拆开给你看。不深入模型架构，不啃神经网络数学，就聊你花钱买到的那份「服务」：它长什么样、按什么收费、怎么「说话」，以及翻车了该怎么办。读完之后，你再看任何大模型产品，都会条件反射地翻译成一封封 HTTP 请求。

主线交代一句：现在这些接口长得都差不多，因为大家默认照着 OpenAI 定的格式抄。所以本文讲的是「OpenAI 那套格式」，具体的例子是我拿 DeepSeek（兼容 OpenAI）真 key 实测的。不过别把话说满：Claude 走的是 Anthropic 自家格式，Gemini 原生也另有一套（后来才补了 OpenAI 兼容入口）——真正照抄 OpenAI 的是 DeepSeek、通义、智谱、Ollama 这一批。路线就清楚了：先看请求怎么发出去、翻车了怎么收拾，再看它按什么收钱、怎么「说话」，最后聊聊市面上三种主流的 API 格式。

## 发送请求：把话打包寄出去

### 上手：真发一条消息

先上最小例子。什么都不引入，一条命令，你就能让一个市值千亿的公司替你说句话：

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-flash",
    "messages": [{"role": "user", "content": "用一句话解释什么是递归"}]
  }'
```

回车，三秒钟后 JSON 回来了（实测真实返回，节选）：

```json
{
  "model": "deepseek-flash",
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "递归就是函数（或过程）直接或间接地调用自身，把一个大问题不断分解成结构相同的更小问题来解决。",
      "reasoning_content": "We need answer in Chinese..."
    },
    "finish_reason": "stop"
  }],
  "usage": { "prompt_tokens": 88, "completion_tokens": 100, "total_tokens": 188 }
}
```

有没有发现一个反直觉的地方？你问的是「递归」，它回了一段挺标准的定义，但 `completion_tokens` 里一大半是 `reasoning_content`——意思是它在「开口」之前，先在脑子里开了一场小会。这是新一代「推理模型」的默认姿势，后文的「计价」和「流式输出」还会撞见它。

把整件事画出来就是这张图：

![一次 LLM API 调用的旅程](fig-journey.svg)

从左往右读：你的代码把 JSON 打包 POST 出去，网关验 key、数请求，GPU 再一个 token 一个 token 地「写」答案，攒成 JSON 原路返回。就这。想用 Python，官方 SDK 长这样：

```python
from openai import OpenAI
client = OpenAI(api_key="...", base_url="https://api.deepseek.com")

r = client.chat.completions.create(
    model="deepseek-flash",
    messages=[{"role": "user", "content": "用一句话解释什么是递归"}],
)
print(r.choices[0].message.content)
```

两段代码干的是同一件事，只是 SDK 帮你把 HTTP 和 token 计数藏起来了。请求里真正必不可少的东西，就三样：`model`（点谁）、`messages`（你说的话）、`Authorization`（你掏钱的身份证明）。剩下全是可选。

三样里最要紧的是那把 `Authorization`，也就是 key。OpenAI 家把它放在标准头 `Authorization: Bearer` 里，Anthropic 家放进自定义头 `x-api-key`，还要求带个版本头——前者谁都熟，后者在只此一家的官方服务上很优雅，本文跟 OpenAI 这套走。至于 key 本身：把它当一张没有交易密码的信用卡，只进服务端环境变量，别写进代码、别提交 git、尤其别放前端。浏览器里的东西，用户都能扒出来。

### 报文：值得认识的字段

先把完整的样子摆出来，免得你看完一堆字段还拼不出整体。一个「写请假邮件」的请求，长这样：

```jsonc
{
  "model": "deepseek-flash",                       // 点谁
  "messages": [                                    // 你说的话，一个数组
    {"role": "system", "content": "你是资深职场助手"},
    {"role": "user",   "content": "帮我写一封请假邮件"}
  ],
  "max_tokens": 2048,                              // 最多输出多少 token
  "temperature": 0.7                               // 随机性旋钮（可省略）
}
```

就这么一段 JSON，`POST` 出去，那边吐回一段。这条我实测过：`finish_reason` 是 `stop`，正常回了封邮件模板。其余字段全是可选的——大多数请求，`model` + `messages` 两样就够开工。想要更精细地控制，值得认识的字段一只手数得过来：

- `model`：点谁。唯一真正影响价格和能力的一栏。
- `messages`：你说的话，一个数组。下面接着说它。
- `max_tokens`：最多让它吐多少 token（别急，「词元账本」马上解释）。一道硬上限，防止一句「简单解释」被它发挥成小论文。提醒一句：设太小会先被「思考」吃光，正文可能连头都没露就结束。
- `temperature`：随机性旋钮。有意思的是，这个过去人人必调的参数，在新一代「先想后答」的模型上基本被架空了——它们自己决定怎么想，不太吃这套。我拿 DeepSeek 传了个 0.7，没报错，但估摸着作用有限。
- `stream`：流式开关，「流式输出」一章的主角。
- `response_format`：要它吐 JSON 而不是散文时用。

`messages` 里每条消息带一个 `role`，一共三种：

![消息列表：一场三人转](fig-messages.svg)

- `system`：剧组的导演，负责立人设、定规矩——「你是资深职场助手」「别超过 200 字」。不参与对话轮次。
- `user`：甲方的话。
- `assistant`：乙方之前说过的话。

关键就一条：**API 无状态，它记不住上一轮说了什么，全靠你每轮把完整历史原样塞回去**。删掉哪段历史，它就「忘掉」哪件事；中间那条 assistant 消息你要是截断了、改乱了，它的表现就忽好忽坏——这不是它抽风，是你历史拼错了。我拿两轮对话实测了一下：

```python
messages = [
    {"role": "system", "content": "你是惜字如金的助手，每句话不超过 5 个字"},
    {"role": "user", "content": "我是谁"},
    {"role": "assistant", "content": "你没说过"},          # 上一条它自己说的
    {"role": "user", "content": "我刚才问了什么"},
]
```

它回「你问我是谁」——正是靠我把那条 assistant 历史原样塞回去，它才「记得」。简单说，把 `messages` 当成一个只追加的日志，每轮结束 push 两条（你的话 + 它的回复），下次整体发出去，就对了。

至于剩下的字段（`stop`、`seed`、`top_p` 之类），都是锦上添花，用到再查文档，别在入门期耗神。这也是我的真心建议：**别上来群拧旋钮**，新一代模型的默认值就是厂商认为的最优值，你只需要在「让不让它多想」之间做个决定。

### 报错：先看状态码

接口翻车时倒不吵不闹，通常只甩给你一个 HTTP 状态码和一段 JSON 错误体。先把状态码认识一遍：

| 状态码 | 含义 | 能重试吗 |
|---|---|---|
| 400 | 请求体不合法（缺字段、JSON 写错） | 不能，改了再发 |
| 401 | 认证失败（key 错、被吊销） | 不能 |
| 403 | 没权限（key 没开通该模型） | 不能 |
| 404 | 模型名拼错（OpenAI 官方的语义） | 不能 |
| 413 | 请求太大 | 不能 |
| 429 | 限流（太密 / 超配额） | 能，按提示等 |
| 500 / 503 | 服务端出错 / 过载 | 能，等一等再试 |

我实测了两条错误体，长得都很直白。一条是把 key 改错：

```json
{
  "error": {
    "message": "Authentication Fails, Your api key: ****RONG is invalid",
    "type": "authentication_error"
  }
}
```

一条是把模型名拼错：

```json
{
  "error": {
    "message": "The supported API model names are deepseek-flash, deepseek-v4-pro, but you passed no-such-model.",
    "type": "invalid_request_error"
  }
}
```

两个坑值得提前踩：一是**模型名拼错的语义各家不一样**——OpenAI 官方返回 404（把模型 ID 当资源），DeepSeek 返回 400。所以「按状态码写死分支」的代码换厂商就失灵。二是 429 的响应头里藏着限流情报（`retry-after` 等几秒），尊重它，别硬刚。

## 词元账本：按字收费

### 分词：它不识字，只数片

模型不识字，识字的是分词器。你发过去的「用一句话解释什么是递归」，它先切成一小块一小块的「词元」，学名 token。切分规则由各家训练好的分词器决定，有时切得很反直觉：`http://` 可能是一个 token，某个生僻人名反而碎成四五片，像被当成错别字拆开审问。

![Token：把话切碎，按片计价](fig-token.svg)

这里有个实用的教训：**别拿字符数去估 token 数，会吓到你自己。** 各家的切法都不一样，最省事的办法是看每次响应里的 `usage` 字段——上面那条「用一句话解释什么是递归」共 10 个字，`prompt_tokens` 却是 88，差着八倍多。另外上下文窗口是个硬天花板（DeepSeek 这代是 1M token），塞满之后质量和速度都掉，超出的部分直接截掉，模型根本看不见。

### 计价：读便宜，写贵

计费最反直觉的一点：**输入比输出便宜**。DeepSeek v4 的价目表（空闲时段，每百万 token）：

| 模型 | 输入 | 输入（命中缓存） | 输出 |
|---|---|---|---|
| `deepseek-flash` | 1 元 | 0.02 元 | 4 元 |
| `deepseek-v4-pro` | 4.5 元 | 0.15 元 | 13.5 元 |

（高峰时段翻倍；上表是北京时间的空闲价。）两个比例值得记住：输出是输入的 3~4 倍；命中缓存便宜了一个数量级。为什么输出贵？读输入像整批原料过库房，能并行；输出像一道菜一道菜现做，只能串着来。于是省钱第一式是：**贵的不是「问得多」，是「答得多」**——让模型写一句话，和写两千字，价差是量级的。还有笔隐藏账：那个 `reasoning_content`（思考过程）也算在输出的 token 里，你问 1+1，它可能先想 200 个 token 再说答案。

看懂了这张表，「点哪个模型」也就有了答案。以 DeepSeek v4 为例：`pro` 比 `flash` 贵三四倍，智力也高一档——上面那个「解释递归」，`flash` 答得标准，`pro` 多补了「直到满足终止条件才逐层返回」这一层。泛化到所有厂商，选型从来不是技术问题，是经济问题：写草稿、贴标签、批量改格式，便宜货绰绰有余；啃长文档、做长链条推理，再掏旗舰的钱。

### 缓存：命中了就便宜

很多请求的长前缀是重复的——系统提示词、工具定义、长文档背景，每次原价重发纯属浪费。各家都有「提示词缓存」：相同前缀命中后按折扣计价。我拿同一段长提示词连发两次，`usage` 里看得明明白白：

```text
第一次  prompt_cache_hit_tokens=0     miss=140   ← 冷缓存，全价
第二次  prompt_cache_hit_tokens=128   miss=12    ← 128 个 token 命中缓存
```

为什么能省这么多？因为模型处理输入时，会给每个 token 算出一套 attention 中间状态，业内叫 **KV Cache**——K 是 Key、V 是 Value，相当于它「读」这段文字时留下的草稿。提示词缓存干的就是把这套草稿存起来：下次请求的开头如果一模一样，服务端直接复用上一轮的 KV Cache，跳过重复计算。便宜的不是「文字重复」，是「省掉了一遍重算」。也正因如此，缓存只能命中最前面那段连续相同的部分——中间改一个字，从那个字往后全得重算。

说白了就一句：**万年不变的内容放前面，每次在变的内容放后面**。别在开头塞时间戳，否则缓存全废。

## 流式输出：让 AI 开口说话

### 逐字：边走边想

你多半以为模型是先在脑子里想好完整答案，再一次性打出来的。不是。它一次吐一个 token，吐完接到句尾，再猜下一个。你看到的完整回复，是这么一个个蹦出来的，只是快得你看不清衔接处。

于是它有两个直接后果。其一，**它不是想好了再写，是边走边想**——会写错、会跑偏、会写到一半发现自己前面说岔了又硬着头皮圆回来。你可以把它理解成一只嘴瓢速度极快的鹦鹉，只是它的嘴瓢常常带着公式。其二，它可以边生成边发送——这就是 `stream`。不开流式，你得等它整段吐完才一次性收到；开了流式，它吐一个 token 你收一个字，体验跟打字机一样。首字延迟从「十几秒」降到「零点几秒」，用户的耐心就是这么省下来的。

![流式：让 AI 从寄快递变成打电话](fig-stream.svg)

### 拆帧：流里流着什么

实现上，加了 `"stream": true` 之后，响应不再是单个 JSON，而是一条 SSE（Server-Sent Events）长连接——普通 HTTP，服务端不断吐 `data:` 开头的行。想看这条流，一行 curl 就行，但先认识一下命令里的 `-N`：它是 `--no-buffer` 的简写，即「关闭缓冲」。curl 默认会对输出做缓冲，一旦输出不是直接打在终端上（比如接了管道或重定向到文件），它就像过于稳重的服务员，非要把菜全攒齐再上桌。普通请求看不出区别，流式响应就致命了——不关缓冲，所有 SSE 帧会憋到 `[DONE]` 才一次性出现，「逐字蹦」的效果直接没了。

```bash
curl -N https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-flash",
    "messages": [{"role": "user", "content": "用一句话解释什么是递归"}],
    "stream": true
  }'
```

我实测的原始流长这样，这里藏着一个推理模型的细节：**它先流「思考」、再流「正文」**：

```text
data: {"choices":[{"delta":{"content":null,"reasoning_content":"We need"}}]}
data: {"choices":[{"delta":{"content":null,"reasoning_content":" answer in Chinese"}}]}
...                              ← 先是一串 reasoning_content 的思考流
data: {"choices":[{"delta":{"content":"递归就是"}}]}
data: {"choices":[{"delta":{"content":"函数调用自身"}}]}
...                              ← 然后才是 content 正文逐字蹦
data: [DONE]
```

用 SDK 时这些拆帧都封装好了，你拿到的是「一段段文本」，认准 `choices[0].delta.content` 拼起来就行。我实测让它写一句五言诗，逐字蹦出来的是「山静松声远」。两个小坑提前说：一是流式默认不返回用量，想要就在请求里加 `"stream_options": {"include_usage": true}`；二是断流没有续传协议，断了就重新发一次，前端对已显示的内容去重即可。

## 三种格式：OpenAI、Anthropic、Responses

### OpenAI 格式：你刚学会的这套

你刚学会的这套就是 OpenAI 格式，学名 Chat Completions：`POST /chat/completions`、`Authorization: Bearer`、`messages` 数组、`finish_reason` 收尾、`prompt_tokens` / `completion_tokens` 记账。它为什么是「普通话」？因为 DeepSeek、通义、智谱、Ollama 全在照抄，官方 `openai` 库也支持自定义 `base_url`：

```python
client = OpenAI(api_key="...", base_url="https://api.deepseek.com")   # 只换这一行
```

这一节不用多讲——整篇文章都在说它，下面两节才是新面孔。官方文档在 [Chat Completions API Reference](https://developers.openai.com/api/reference/resources/chat)。

### Anthropic 格式：导演坐到了顶层

Anthropic 家的 Messages API 走的是另一条路，DeepSeek 的兼容口在 `https://api.deepseek.com/anthropic`。请求长这样，`curl` 姿势几乎没变，只是认证头换了：

```bash
curl https://api.deepseek.com/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $DEEPSEEK_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -d '{
    "model": "deepseek-flash",
    "max_tokens": 500,
    "system": "你是资深职场助手",
    "messages": [{"role": "user", "content": "用一句话解释什么是递归"}]
  }'
```

同一个递归问题，实测返回长这样（节选）：

```json
{
  "content": [
    { "type": "thinking", "thinking": "我们需要回答用户中文问题……最终直接回答。", "signature": "1a5cd61f-…" },
    { "type": "text", "text": "递归就是函数或过程通过调用自身，把大问题不断拆成同类的小问题，直到遇到能直接求解的基本情况为止。" }
  ],
  "stop_reason": "end_turn",
  "usage": { "input_tokens": 39, "cache_read_input_tokens": 0, "output_tokens": 167 }
}
```

跟 OpenAI 格式对着看，四处不一样：

- **认证**：不用 `Authorization: Bearer`，改用 `x-api-key` 头；Anthropic 官方还要求带 `anthropic-version` 版本头（实测 DeepSeek 会忽略它，但照带没有坏处）。
- **人设**：`system` 从 `messages` 数组里搬到了顶层——`messages` 里只剩 `user` / `assistant` 两种角色，导演从片场角落坐上了主席台。
- **内容**：`content` 不再是字符串，是「块」的数组——`text` 块、`thinking` 块，各带各的类型。
- **记账**：结束原因叫 `stop_reason`（`end_turn` / `max_tokens` / `tool_use`），用量叫 `input_tokens` / `output_tokens`，缓存字段叫 `cache_read_input_tokens`——跟 `prompt_cache_hit_tokens` 一个意思，换个名字而已。

三句要紧话。其一，上面那个 `thinking` 块就是 `reasoning_content` 在 Anthropic 家的名字——同一个「先想后答」，照样算在 `output_tokens` 里，还带一个 `signature` 签名。其二，官方 Anthropic 的 `max_tokens` 是必填的，实测 DeepSeek 这边不填也能跑——换厂商记得补上。其三，DeepSeek 这个兼容口有个彩蛋脾气：传 `claude-sonnet-5-5` 这类 Claude 模型名不会报错，而是悄悄映射成 `deepseek-flash`；`claude-opus` 开头的映射成 `deepseek-v4-pro`——名字兼容，账还是 DeepSeek 的。想用官方 `anthropic` SDK 的话，把 `ANTHROPIC_BASE_URL` 指到这个地址就行。官方文档见 [Messages API](https://platform.claude.com/docs/en/api/messages)。

### Responses 格式：OpenAI 押注的下一代

Chat Completions 是「聊天接口」，Responses 是「智能体接口」——OpenAI 官方把新东西（联网搜索、工具调用、计算机操作）都往这上面堆，它才是押注的下一代。还是熟悉的 Bearer key，但骨架换了不少：

- `input` 可以直接是一个字符串（也可以是一串「条目」），不用包 `messages` 数组。
- 人设字段叫 `instructions`，顶层平放，替代 `system`。
- 上限字段叫 `max_output_tokens`。
- 响应没有 `choices` 数组，改成 `output[]` 条目数组——`reasoning` 条目、`message` 条目，各带各的类型。
- 结束原因不叫 `finish_reason` 了：`status` 直接告诉你 `completed` 还是 `incomplete`，截断时 `incomplete_details.reason` 交代原因。

实测同一句递归问题：

```bash
curl https://api.deepseek.com/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-flash",
    "instructions": "你是资深职场助手",
    "input": "用一句话解释什么是递归"
  }'
```

```json
{
  "status": "completed",
  "output": [
    { "type": "reasoning", "content": [{ "type": "reasoning_text", "text": "我们需要回答用户中文请求……最终直接回答。" }], "summary": [] },
    { "type": "message", "role": "assistant", "content": [{ "type": "output_text", "text": "递归就是函数或过程通过调用自身，把大问题不断拆成同类的小问题，直到遇到可直接解决的基本情况为止。" }] }
  ],
  "usage": { "input_tokens": 39, "output_tokens": 150, "output_tokens_details": { "reasoning_tokens": 118 } }
}
```

注意两点：`output` 里「思考」是单独一个 `reasoning` 条目，正文是 `message` 条目——边界画得清清楚楚；用量里连「思考花了多少 token」都单列（`reasoning_tokens: 118`），呼应前面那句「贵的不是问得多，是答得多」——想得多也一样算钱。我拿 20 个 token 的小预算试过一次截断，它老实交代 `incomplete_details.reason: max_output_tokens`。流式事件也换了名字：OpenAI 格式是裸的 `data:` 帧，Anthropic 家是 `message_start`、`content_block_delta`、`message_delta` 一套，Responses 家是 `response.created`、`response.output_text.delta`……SDK 都帮你拼好了，认得名字就行。官方文档见 [Responses API Reference](https://developers.openai.com/api/reference/responses/overview)。

### 一张表看清三家

把三家并排摆开，差异一眼见底：

| 维度 | OpenAI 格式 | Anthropic 格式 | Responses 格式 |
|---|---|---|---|
| 请求路径 | `/chat/completions` | `/anthropic/v1/messages` | `/v1/responses` |
| 认证方式 | `Authorization: Bearer` | `x-api-key`（官方还要版本头） | `Authorization: Bearer` |
| 人设字段 | `messages` 里的 `system` | 顶层 `system` | 顶层 `instructions` |
| 输入 | `messages` 数组 | `messages` 数组 + 顶层 `system` | `input` 字符串或条目 |
| 输出上限 | `max_tokens` | `max_tokens`（官方必填） | `max_output_tokens` |
| 结束原因 | `finish_reason` | `stop_reason` | `status` + `incomplete_details` |
| 用量字段 | `prompt_tokens` / `completion_tokens` | `input_tokens` / `output_tokens` | `input_tokens` / `output_tokens` |
| 思考过程 | `reasoning_content` | `thinking` 块 | `reasoning` 条目 |

三套格式，同一门生意：POST + JSON + key、按 token 收钱——一个字都没变，变的是信封。OpenAI 格式胜在「谁都认识」；Anthropic 格式结构更讲究；Responses 是官方押注的下一代，新能力先到它那儿（Gemini 原生也另有一套，这篇先不聊它）。还有一个彩蛋：同一个「先想后答」，三家三个名字——`reasoning_content`、`thinking` 块、`reasoning` 条目。认得出这三个，读哪家的返回都不慌。

![三个信封，同一个收银台](fig-formats.svg)

## 收尾：明码标价

最后聊点实际的。按 token 收费，这笔账很好算：喂进去多少字、吐出来多少字，乘以单价，就是这次调用的成本。想让模型多想几轮，账单就多几行；想用更强的模型，单价就更高。API 这边价格都写在价目表上，没有会员等级，也没有「充多少送多少」的套路，甚至懒得给你发一张优惠券。

下次你在网页里跟 AI 聊到它弹出「继续对话请升级」，就可以在脑子里把它翻译成：这孩子今天吐的 token 有点多，余额见底了。相比把它当成无所不能的智慧体，把它当成一个按字计费的接口来用，你会更清醒，也更省钱。

这一篇只铺了文本 chat 这条主路。前面露过脸的语音、图像只算打卡；**结构化输出**（让它吐 JSON 而不是散文）和 **工具调用**（让它动嘴、你的代码动手）这两块重头戏，还够单独拆一篇。挑一篇值得单开的，我下回拆。你最想先看哪个，评论区说。
