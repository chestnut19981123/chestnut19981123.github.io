---
title: LLM API 使用说明书：从一行 curl 到一句人话
cover: cover.svg
categories: 'AI'
tags: ['AI', 'LLM', 'API']
date: 2026-09-09
---

## 开场：它不是智能，是个接口

先破一个泡泡：你天天跟 AI 聊天，以为屏幕对面坐着一个无所不知的智慧体。其实你每敲一句话，背后发生的是一件特别朴素的事——你的机器往某个域名发了一个 POST 请求，请求体是一段 JSON，顺手附上一把 API Key 当入场券。服务器那边不做别的：收下 JSON，算出一个字，回给你，收钱。如此往复，直到它觉得该闭嘴。

这篇文章要做的，就是把这件事拆开给你看。不聊模型架构，不聊神经网络，就聊你花钱买到的那份「服务」：它长什么样、按什么收费、怎么「说话」，以及翻车了该怎么办。读完之后，你再看任何大模型产品，都会自动翻译成一封封 HTTP 请求。

主线交代一句：现在这些接口长得都差不多，因为大家默认照着 OpenAI 定的格式抄。所以本文讲的是「OpenAI 那套格式」，具体的例子是我拿 DeepSeek（兼容 OpenAI）真 key 实测的。不过别把话说满：Claude 走的是 Anthropic 自家格式，Gemini 原生也另有一套（后来才补了 OpenAI 兼容入口）——真正照抄 OpenAI 的是 DeepSeek、通义、智谱、Ollama 这一批。路线就清楚了：先看请求怎么发出去，再看它按什么收钱、怎么「说话」，最后聊聊翻车了怎么收拾、以及生态里的兼容与选择。

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

有没有发现一个反直觉的地方？你问的是「递归」，它回了一段挺标准的定义，但 `completion_tokens` 里一大半是 `reasoning_content`——意思是它在「开口」之前，先在脑子里过了一遍。这是新一代「推理模型」的默认姿势，后文的「计价」和「流式输出」还会撞见它。

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

三样里最要紧的是那把 `Authorization`，也就是 key。OpenAI 家把它放在标准头 `Authorization: Bearer` 里，Anthropic 家放进自定义头 `x-api-key`，还要求带个版本头——前者谁都熟，后者在只此一家的官方服务上很优雅。本文跟 OpenAI 这套走，Anthropic 那套放到「旁支」小节再露脸。至于 key 本身：把它当一张没有交易密码的信用卡，只进服务端环境变量，别写进代码、别提交 git、尤其别放前端。浏览器里的东西，用户都能扒出来。

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

就这么一段 JSON，`POST` 出去，那边吐回一段。这条我实测过：`finish_reason` 是 `stop`，正常回了封邮件模板。剩下的字段全是可选的——大多数请求，`model` + `messages` 两样就够开工。想要更精细地控制，值得认识的字段一只手数得过来：

- `model`：点谁。唯一真正影响价格和能力的一栏。
- `messages`：你说的话，一个数组。下面单独说它。
- `max_tokens`：最多让它吐多少字。一道硬上限，防止一句「简单解释」被它发挥成小论文。提醒一句：设太小会被「思考」吃光（「截断」那节有实测）。
- `temperature`：随机性旋钮。有意思的是，这个过去人人必调的参数，在新一代「先想后答」的模型上基本被架空了——它们自己决定怎么想，不太吃这套。我拿 DeepSeek 传了个 0.7，没报错，但估摸着作用有限。
- `stream`：流式开关，「流式输出」一章的主角。
- `response_format`：要它吐 JSON 而不是散文时用。

剩下的（`stop`、`seed`、`top_p` 之类）都是锦上添花，用到再查文档，别在入门期耗神。这也是我的真心建议：**别上来群拧旋钮**，新一代模型的默认值就是厂商认为的最优值，你只需要在「让不让它多想」之间做个决定。

### 角色：一场三人转

`messages` 里每条消息带一个 `role`，一共三种：

![消息列表：一场三人转](fig-messages.svg)

- `system`：立人设、定规矩——「你是资深职场助手」「别超过 200 字」。不参与对话轮次。
- `user`：你说的话。
- `assistant`：它之前说过的话。

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

## 词元账本：按字收费

### 分词：它不识字，只数片

模型不识字。你发过去的「用一句话解释什么是递归」，它先切成一小块一小块的「词元」，学名 token。切分规则由各家训练好的分词器决定，有时切得很反直觉：`http://` 可能是一个 token，某个生僻人名反而碎成四五片。

![Token：把话切碎，按片计价](fig-token.svg)

这里有个实用的教训：**别拿字符数去估 token 数，会吓到你自己。** 各家的切法都不一样，最省事的办法是看每次响应里的 `usage` 字段——上面那条「用一句话解释什么是递归」共 10 个字，`prompt_tokens` 却是 88，差着八倍多。另外上下文窗口是个硬天花板（DeepSeek 这代是 1M token），塞满之后质量和速度都掉，超出的部分直接截掉，模型根本看不见。

### 计价：读便宜，写贵

计费最反直觉的一点：**输入比输出便宜**。DeepSeek v4 的价目表（空闲时段，每百万 token）：

| 模型 | 输入 | 输入（命中缓存） | 输出 |
|---|---|---|---|
| `deepseek-flash` | 1 元 | 0.02 元 | 4 元 |
| `deepseek-v4-pro` | 4.5 元 | 0.15 元 | 13.5 元 |

（高峰时段翻倍；上图是北京时间的空闲价。）两个比例值得记住：输出是输入的 3~4 倍；命中缓存便宜了一个数量级。为什么输出贵？读输入能整段并行算，输出得一个 token 一个 token 地串着生。于是省钱第一式是：**贵的不是「问得多」，是「答得多」**——让模型写一句话，和写两千字，价差是量级的。还有笔隐藏账：那个 `reasoning_content`（思考过程）也算在输出的 token 里，你问 1+1，它可能先想 200 个 token 再说答案。

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

于是它有两个直接后果。其一，**它不是想好了再写，是边走边想**——会写错、会跑偏、会写到一半发现自己前面说岔了又硬着头皮圆回来。你不该奇怪它「说漏嘴」，该奇怪的是它居然经常蒙对。其二，它可以边生成边发送——这就是 `stream`。不开流式，你得等它整段吐完才一次性收到；开了流式，它吐一个 token 你收一个字，体验跟打字机一样。首字延迟从「十几秒」降到「零点几秒」，用户的耐心就是这么省下来的。

![流式：让 AI 从寄快递变成打电话](fig-stream.svg)

### 拆帧：流里流着什么

实现上，加了 `"stream": true` 之后，响应不再是单个 JSON，而是一条 SSE（Server-Sent Events）长连接——普通 HTTP，服务端不断吐 `data:` 开头的行。想看这条流，一行 curl 就行，但先认识一下命令里的 `-N`：它是 `--no-buffer` 的简写，即「关闭缓冲」。curl 默认会对输出做缓冲，一旦输出不是直接打在终端上（比如接了管道或重定向到文件），数据就会被攒起来，等整个连接结束才一次性吐出来。普通请求看不出区别，流式响应就致命了——不关缓冲，所有 SSE 帧会憋到 `[DONE]` 才一次性出现，「逐字蹦」的效果直接没了。

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

## 错误处理：让调用扛住生产

### 报错：先看状态码

接口不会一直好脾气。它翻车的方式很规律：一个 HTTP 状态码，加一段 JSON 错误体。先把状态码认识一遍：

| 状态码 | 含义 | 能重试吗 |
|---|---|---|
| 400 | 请求体不合法（缺字段、JSON 写错） | 不能，改了再发 |
| 401 | 认证失败（key 错、被吊销） | 不能 |
| 403 | 没权限（key 没开通该模型） | 不能 |
| 404 | 模型名拼错（OpenAI 官方的语义） | 不能 |
| 413 | 请求太大 | 不能 |
| 429 | 限流（太密 / 超配额） | 能，按提示等 |
| 500 / 503 | 服务端出错 / 过载 | 能，退避重试 |

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

### 退避：别硬刚 429

![被 429 拒绝后：硬发 vs 指数退避](fig-retry.svg)

遇到 429，新手的本能是「马上再发」，于是收到第二个 429。正确的做法是**指数退避**：失败等 1 秒，再失败等 2 秒、4 秒、8 秒……每次翻倍。而且只对「值得重试」的错误重试——429、5xx、断网，重试；400、401、403，重试一万次也一样。用 SDK 时这基本免费（官方默认对 429/5xx 退避重试），裸 curl 才需要自己写。顺带提醒：重试会双重扣费，第一次可能已经生成完了、只是响应丢了。

## 兼容生态：一套代码，八方通用

### 兼容：换个 base_url 就走

![兼容生态：同一个 SDK，不同的底座](fig-eco.svg)

这里揭晓开场埋的伏笔：为什么换厂商「一字不改」？因为 OpenAI 的 chat/completions 格式是行业事实标准，DeepSeek、通义、智谱、Ollama 全在照抄，官方 `openai` 库支持自定义 `base_url`：

```python
client = OpenAI(api_key="...", base_url="https://api.deepseek.com")   # 只换这一行
```

我拿这行实测跑通了一个请求（返回 `finish_reason: "stop"`、`total_tokens: 166`）。但「兼容」是约等于，不是等于——错误码语义、必填项、模型名各家都有小脾气，换厂商前把差异文档过一遍，坑多半就踩在这些「约等于」上。

### 旁支：除了聊天，还有这些接口

`chat/completions` 是最大的一块，但「按 token 计价的接口」其实是一大家子。它们都长一个样——同一个 base_url、同一把 key，只是路径和进出字段不同。前面学的「POST + JSON + Bearer key」那套姿势，换到哪个接口都能复用。

**嵌入**：`POST /v1/embeddings`，文本进、一长串浮点数出，干的是「比较两段文字像不像」的活——RAG、语义搜索、聚类全靠它。OpenAI 定了格式，各家照抄（顺带说一句，DeepSeek 目前没有这个接口，别在它家白找）。

**补全**：`POST /v1/completions`，没有 `messages` 数组，就一个 `prompt` 进、一段文本出，是 chat 的老前辈。如今日常基本被 chat 取代，只剩「补中间代码」这类 FIM 活儿还在用它。

**模型**：`GET /v1/models`，一个 GET，回一张你家有哪些模型的清单。写代码前先摸一眼，模型名拼没拼错就心里有数了——我开头能顺利跑通「解释递归」，第一步就是先查了模型清单。

**语音、图像**：再往外还有 `audio/speech`（文字→语音）、`audio/transcriptions`（语音→文字，Whisper 那套）、`images/generations`（文字→图）。这些 DeepSeek 没有，各厂商各实现一部分，套路一样：同一个 SDK、同一把 key，换 URL、换字段。

**批处理、文件、审核**：再往外还有 `batches`（不急的请求打包、半价排队）、`files`（上传文档给模型看）、`moderations`（先查内容合不合规），都是同一个 base_url 下的不同路径。

所以这一篇的功夫没白费——你学会的不是「某一个接口」，是这一整家人的说话方式。

## 收尾：明码标价

最后聊点实际的。按 token 收费，这笔账很好算：喂进去多少字、吐出来多少字，乘以单价，就是这次调用的成本。想让模型多想几轮，账单就多几行；想用更强的模型，单价就更高。价格都写在价目表上，没有会员等级，也没有「充多少送多少」的套路。

下次你在网页里跟 AI 聊到它弹出「继续对话请升级」，就可以在脑子里把它翻译成：这孩子今天吐的 token 有点多，余额见底了。相比把它当成无所不能的智慧体，把它当成一个按字计费的接口来用，你会更清醒，也更省钱。

这一篇只铺了文本这条主路。接口还有另一半地图没展开：**结构化输出**（让它吐 JSON 而不是散文）、**工具调用**（让它动嘴、你的代码动手），还有多模态这些旁支。挑一篇值得单开的，我下回拆。你最想先看哪个，评论区说。
