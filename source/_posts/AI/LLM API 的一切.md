---
title: LLM API 的一切:从一行 curl 说起
cover: cover.svg
categories: 'AI'
tags: ['AI', 'API']
date: 2026-09-08
---

## 开场:它不是魔法,是一个 HTTP 接口

先讲一个场景。你第一次搞到大模型 API 的 key 时,大概和我一样:先在网页聊天框里玩得不亦乐乎,然后打开官方文档,面对几十个参数和两家不兼容的格式,内心 OS 是「我只是想让它帮我写个周报,为什么要先读三天文档」。

直到有人甩给你一行 curl:

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{"model":"deepseek-v4-flash","messages":[{"role":"user","content":"你好"}]}'
```

回车。三秒钟后,JSON 回来了。那一刻你才意识到:哦,原来聊天网页背后也是这么一发请求——**大模型不是魔法,是一个普通的 HTTP 接口**。你调过天气 API、调过支付回调,调它没有任何本质区别:发个 POST,收个 JSON,按字段解析,仅此而已。

这篇文章想把「LLM API」这块从头到尾讲透:从第一行 curl,到双 API 格式对照,到 token 计费、流式、限流重试,再到「一套代码跑遍所有大模型」的兼容生态。为了写这篇,我拿真 key 实测了几十次调用,账单合计不到一毛钱——这也是你学 API 的第一课:**它真的会扣钱**,以及**它真的便宜到可以随便造**。

> 文章里的示例全部真实可跑:我在 DeepSeek 的 OpenAI 兼容端点和 Anthropic 兼容端点上逐条实测过,正文标注了实测结果;官方 OpenAI / Anthropic 端点结构与示例逐字段一致(差异处有注明)。你只需要一个 key 就能把全文例子跑一遍——顺带说,这正是本文第六章要讲的兼容生态。

## 第一章 · 一次调用的全貌:把第一句话送出去

### 1.1 一次调用到底发生了什么

先把全景图记住,后面每一章都是这张图上的一个放大镜。

![一次 LLM API 调用的旅程](fig-journey.svg)

从左往右读:你的代码把一段 JSON 打包成 HTTP POST,丢给 API 的网关。网关先验明正身(认证)、看看你有没有超频(限流),然后把它转给背后的一排 GPU。模型在 GPU 上逐字「写」出回答——不是一次性吐出来,而是一个 token 一个 token 地生成——攒成 JSON 再原路返回。

注意三个细节,后面都会用到:

1. **模型不记你**。API 是无状态的:它不保存你的聊天记录,你每次都得把整个对话历史一起发过去(第二章细说)。就像每次打电话都要从头自我介绍一遍的同事。
2. **认证靠请求头**。key 不放在 URL 里,也不放在请求体里,而是放在 HTTP header 中(下节讲)。
3. **计费看 token**。你花的每一分钱都对应着「处理了多少 token」,不是按次数算的(第三章讲)。

### 1.2 端点与认证:两个流派

2026 年的 LLM API 江湖,主流格式就两家:OpenAI 系和 Anthropic 系。其他厂商(DeepSeek、通义、智谱、Kimi……)基本都站队 OpenAI 系,少数(比如 DeepSeek 的 Anthropic 兼容端点)两头通吃。先看两家官方怎么发请求:

| | OpenAI(及兼容系) | Anthropic |
|---|---|---|
| 端点 | `POST https://api.openai.com/v1/chat/completions` | `POST https://api.anthropic.com/v1/messages` |
| key 放哪 | `Authorization: Bearer sk-...` | `x-api-key: sk-ant-...` |
| 必带版本头? | 无 | `anthropic-version: 2023-06-01` |
| 请求体主字段 | `model` + `messages` | `model` + `max_tokens` + `messages` |
| 计费字段名 | `prompt_tokens` / `completion_tokens` | `input_tokens` / `output_tokens` |

两家最大的「格式差异」其实不是参数名,而是**认证哲学**:OpenAI 用标准的 `Authorization: Bearer`(任何一个做过 Web 开发的人都熟),Anthropic 则把 key 放进自定义头 `x-api-key`,还要求带一个 `anthropic-version` 版本头——API 演进时,老客户端靠这个头声明「我按 2023 年的规矩来」,不会因为服务端升级而突然坏掉。这套设计在「只此一家」的官方服务上很优雅,但等会儿你会看到,兼容层厂商对它是又敬又怕。

### 1.3 第一行 curl:真发一条消息

下面两条是我实测跑通的。第一条是 OpenAI 兼容格式,第二条是 Anthropic 格式——用的同一个 key、同一个 DeepSeek 账号(端点不同而已)。把 `$DEEPSEEK_API_KEY` 换成你自己的 key(建议先 `export DEEPSEEK_API_KEY=sk-...`)。

**OpenAI 兼容格式**(实测于 `api.deepseek.com`,OpenAI 官方同构:换成 `https://api.openai.com/v1/chat/completions` 和官方模型名即可):

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "用一句话介绍你自己"}]
  }'
```

响应(节选,真实返回):

```json
{
  "id": "1d988754-...",
  "object": "chat.completion",
  "model": "deepseek-v4-flash",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "你好",
      "reasoning_content": "我们只需要回复两个字"
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 89,
    "completion_tokens": 10,
    "total_tokens": 99
  }
}
```

**Anthropic 格式**(实测于 `api.deepseek.com/anthropic`,Anthropic 官方同构:换成 `https://api.anthropic.com/v1/messages`,并且要另带 `anthropic-version: 2023-06-01` 头):

```bash
curl https://api.deepseek.com/anthropic/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-v4-flash",
    "max_tokens": 1024,
    "messages": [{"role": "user", "content": "用一句话介绍你自己"}]
  }'
```

响应(节选,真实返回):

```json
{
  "id": "39859c1a-...",
  "type": "message",
  "role": "assistant",
  "model": "deepseek-v4-flash",
  "content": [
    {"type": "text", "text": "你好"}
  ],
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 89,
    "output_tokens": 9
  }
}
```

两条响应放在一起看,一眼就能认出两家的基因:OpenAI 的响应是个「数组套对象」(`choices[0].message.content`,为未来可能输出多个候选留了位置),Anthropic 的响应是个「内容块列表」(`content` 数组里每块带 `type`,文本是 `text` 块,以后还能有 `tool_use` 块、`thinking` 块……)。字段名不同,灵魂一样:**都告诉你模型说了什么、为什么停下来、花了多少 token**。

顺带说,上面响应的 `reasoning_content` 和 `thinking` 块其实是「推理模型」的产物——你问了个简单问题,模型还是先在脑子里过了一遍。这是 2026 年的大趋势,后面第三章还会遇到它。

### 1.4 key 的安全课:它就是钱

把 key 看成一张**无限额度的信用卡**,你大概就懂该怎么对它了:

- 它只该出现在服务端环境变量里,不该写进代码、不该提交进 git(加进 `.gitignore`)、**尤其不该放在前端代码里**——浏览器里的任何东西用户都能扒出来,扒出来就是敞开的钱包。
- 泄露了立刻去控制台吊销重建,别心疼。
- 各家 key 的作用域不同:有的能设额度上限、有的能限定可用模型,真怕手滑就都配上。
- 我实测时故意用错 key 发了一次请求,返回的 401 错误体长这样:

```json
{"error": {"message": "Authentication Fails, Your api key: ****-123 is invalid",
           "type": "authentication_error"}}
```

看,连错误提示都这么直接。第五章会把这套错误码系统完整过一遍。

## 第二章 · 请求体:把一场对话打包寄出去

### 2.1 字段解剖:两边各有什么旋钮

先看两家请求体并排的完整形态(以「帮我写一封请假邮件」为例):

```jsonc
// OpenAI 兼容格式
{
  "model": "deepseek-v4-flash",          // 用哪个模型
  "messages": [                          // 对话历史,数组
    {"role": "system", "content": "你是资深职场助手"},
    {"role": "user", "content": "帮我写一封请假邮件"}
  ],
  "temperature": 0.7,                    // 随机性旋钮(经典参数,见下)
  "max_tokens": 1024                     // 输出上限
}
```

```jsonc
// Anthropic 格式
{
  "model": "deepseek-v4-flash",
  "system": "你是资深职场助手",            // 注意:system 独立成字段
  "messages": [
    {"role": "user", "content": "帮我写一封请假邮件"}
  ],
  "temperature": 0.7,
  "max_tokens": 1024                     // Anthropic 必填
}
```

一眼能看出的差异:`system` 提示词在 OpenAI 系是一条普通消息(`messages` 里 role 为 `system` 的那条),在 Anthropic 系是**独立顶层字段**。其余字段大同小异,一张表讲完:

| 字段 | 作用 | 注意 |
|---|---|---|
| `model` | 选模型 | 最影响价格与能力,没有之一 |
| `messages` / `system` | 对话内容 | 无状态:全量历史都要你带 |
| `temperature` | 输出随机性旋钮 | **正在消失的参数**:Anthropic 新一代旗舰直接移除(传了就 400);OpenAI 系只在特定配置下接受;经典模型仍可用。各家范围还不同(DeepSeek 兼容层是 0.0–2.0) |
| `top_p` | 老牌采样参数 | 与 temperature 二选一用,地位同样在缩水 |
| `max_tokens` | 输出 token 上限 | OpenAI 新一代模型改叫 `max_completion_tokens`(推理 token 也算输出);Anthropic 官方一直必填 |
| `stream` | 流式开关 | 第四章主角 |
| `stop` / `stop_sequences` | 自定义终止符 | 生成到该字符串就停 |
| `seed` | 尽量复现结果 | OpenAI 系的「尽量」玄学,不作保证 |
| `response_format` / `output_config.format` | 强制输出 JSON 等结构化格式 | 各家名称不一,用途相同 |

看见那两行「正在消失的参数」了吗?这是 2026 年 API 圈的真实笑点:过去调 prompt 的人最爱拧 `temperature`,如今新一代模型直接把它 400 掉——「调参时代落幕了,我们替你调」。你写代码时与其纠结 0.7 还是 0.8,不如记住:**新一代模型的默认值,就是厂商认为的最优值**。

### 2.2 消息与角色:一场没有剧本的戏

请求体里真正花心思的是 `messages`。它是一段**对话历史**,每条消息带一个 `role`,总共三种:

![消息列表:一场三人转](fig-messages.svg)

- **`system`(舞台提示)**:给模型立人设、定规矩——「你是资深职场助手」「回答不超过 200 字」「不要提你是 AI」。Anthropic 系它在顶层字段,OpenAI 系它在数组里。它不参与「对话轮次」,只是开场前的布景。
- **`user`(观众发话)**:你说的话,以及(在多轮工具调用里)工具执行结果。
- **`assistant`(演员回话)**:模型之前说过的话。**多轮对话时,你必须把自己收到的每一条 assistant 回复原样塞回去**——还记得吗,API 无状态,模型不记得上一轮说过什么,全靠你每次把完整剧本重新递上去。

三条规则要背熟,违反就是 400:

1. **第一条消息必须是 `user`**(Anthropic 系还会要求 user/assistant 严格交替,OpenAI 系宽松些)。
2. **assistant 消息必须原样回传**,一个字都不能改——改了模型会以为你篡改了它的记忆(新版 Anthropic 甚至能检测出「对话被编辑过」,直接报错)。
3. 想要模型记住什么,就把历史里都带上;想要它忘掉什么,就别把那段历史发过去——**删除即遗忘**。

有个经典错误值得单独拎出来:很多人以为把「上一条回答」存数据库、下次查出来拼回去就行,结果拼出来的历史里 assistant 消息被截断了、顺序错了,模型表现忽好忽坏。这不是模型抽风,是你的剧本有 bug。多轮对话的正确姿势是**把消息数组当成一个只追加的日志**,每轮结束原样 push 两条(你的话 + 它的回复),下次整体发出去。

### 2.3 进阶字段速览:工具调用与结构化输出

请求体还能装更多东西,篇幅所限只快速点名,深水区留给之前的文章:

- **工具调用(Function Calling / Tool Use)**:在请求里附上 JSON Schema 描述的工具列表,模型就能在回复里「请求」调用工具(返回 `tool_calls` / `tool_use` 块),由你的代码真正执行。这是 Agent 的地基——我写过一篇《Agent 实现原理》,把那套「模型只动嘴、代码才动手」的往返拆了个底朝天,想看深度的去那篇,这里只放两家格式对照:

```jsonc
// OpenAI 系回复中的工具请求
{"role": "assistant",
 "tool_calls": [{"id": "call_00_...", "type": "function",
                 "function": {"name": "get_weather",
                              "arguments": "{\"city\": \"北京\"}"}}]}
```

```jsonc
// Anthropic 系回复中的工具请求(content 块)
{"role": "assistant",
 "content": [{"type": "tool_use", "id": "toolu_...",
              "name": "get_weather", "input": {"city": "北京"}}]}
```

注意 OpenAI 系连参数都是**字符串**(`"arguments": "{\"city\": ...}"`,要再 parse 一次),Anthropic 系直接给对象——细节之处的性格差异。两条我都实测过,模型在拿不准时会真的发起工具请求而不是瞎编,`finish_reason` / `stop_reason` 会告诉你它为什么停(`tool_calls` / `tool_use`)。

- **结构化输出**:`response_format: {"type": "json_object"}`(OpenAI 系)或 schema 约束,让模型输出保证可 parse 的 JSON,省去你自己抽字符串的苦。
- **seed、presence_penalty 之类**:锦上添花的旋钮,用到再查文档,别在入门期浪费注意力。

好,请求包好了。接下来是这行请求真正花钱的地方:token。

## 第三章 · Token:LLM 的货币与钱包

### 3.1 tokenizer:模型眼里的文字是碎末

模型不看「字」,看「token」。token 是模型处理文本的最小单位,大致是「半个词」到「一个词」的碎片:英文里 `hello world` 可能被切成 `hello` + ` world` 两个 token,中文一个字大概对应 1–2 个 token。切分规则由各家训练好的 **tokenizer** 决定——它不是按字典切的,而是按训练数据里的高频片段切的,所以有时切得很反直觉(比如 `http://` 可能是一个 token,某个生僻人名反而碎成四五片)。

![token 切分与上下文窗口](fig-token.svg)

几个必须建立的直觉:

1. **别猜,要数**。每家的 tokenizer 都不同,「这段话几个 token」只有调接口才知道——Anthropic 有 `/v1/messages/count_tokens`,OpenAI 系的 SDK 也都有估算方法,更省事的做法是看响应里 `usage` 字段(每次调用都会如实报告,前面实测里 `prompt_tokens: 89` 那种)。**拿字符数乘个系数当 token 数估算,是账单惊吓的常见来源**。
2. **上下文窗口是硬天花板**。模型一次能「看到」的 token 总数有限(2026 年的旗舰普遍几十万到上百万,但别被这个数字骗了——塞满之后质量和速度都下降,还贵)。超出窗口的部分会被直接截掉,模型根本看不见。
3. **输出同样按 token 计**。`max_tokens` 限的是输出长度;模型写到上限会硬停,`finish_reason` 会告诉你 `max_tokens`(被截断)还是 `stop` / `end_turn`(自然说完)。**写代码务必检查这个字段**——被截断的回答经常是半句话,直接拿给用户看会闹笑话。

### 3.2 计费的不对称美学:贵的是输入,不是输出

token 计费最反直觉的一点:**输入比输出便宜**。以 Anthropic 官方 2026 年中的价格为例,旗舰模型的输入单价是输出的五分之一(输入 $5/百万 token,输出 $25/百万 token,各家比例类似但价格变动频繁,以官网为准)。为什么?因为输入要跑一遍完整的神经网络前向,输出是边生成边算——等等,其实反过来:输出才是逐 token 生成、最贵的部分。输入像复印一摞文件(一次过),输出像现场写一篇作文(逐字斟酌)。

这条不对称直接推导出省钱第一定律:**贵的不是「问得多」,是「答得多」**。同一个问题,让模型输出 100 字的总结和输出 2000 字的长文,价格差着量级。别让模型给你长篇大论当你只需要一句话时。

### 3.3 省钱的科学:缓存、裁剪与批处理

再往下一层,账单的大头往往不是你想的那样。三个实战技巧:

**① 提示词缓存(Prompt Caching):复用的前缀打骨折。**

很多请求的长文本前缀是重复的:系统提示词、工具定义、长文档背景……每次原价重发纯属浪费。各家都有缓存:相同前缀命中后,命中的部分按接近一折计价,响应里会报告命中了多少(`prompt_tokens_details.cached_tokens` / `cache_read_input_tokens`,我在实测里见过这个字段——它一直是 0 的话,说明你的前缀每次都在变,缓存一次没命中)。

> 缓存的前提是**前缀逐字节稳定**:系统提示词里放个时间戳、JSON key 顺序每次不同,缓存就全废了。把「每次都在变的东西」放到请求末尾,「万年不变的东西」放前面。

**② 输入裁剪:你发出去的每个字都在付钱。**

无状态 API 意味着每轮对话都要重发全部历史——聊了 50 轮的客服机器人,每次请求都背着前面所有轮次。历史太长时,主动截断或摘要(把旧轮次压成一段「前面聊了什么」),既省钱又不容易把窗口塞爆。我在《Agent 实现原理》里写过 Agent 的自动压缩策略,思路同源:窗口是租来的,别把它当硬盘用。

**③ 批处理(Batch API):不急的请求,半价排队。**

两家官方都提供批处理:把几千个请求打包提交,24 小时内异步跑完,价格约为实时的一半。适合离线任务:批量翻译、批量打标、批量总结。实时聊天用不上,但如果你有「每天晚上跑一次」的活,这是白捡的折扣。

**④ 别忘了推理 token 也在计费。**

还记得开场实测里的 `reasoning_content` 吗?2026 年的模型普遍会先「思考」再回答,思考过程也是输出 token,照样计费。你问「1+1=?」,模型可能先想 200 个 token 再说答案——这不是 bug,是新一代模型的工作方式,账单里看得明明白白(`completion_tokens_details.reasoning_tokens`)。想省,就选不需要深度推理的轻量模型干杂活。

## 第四章 · 流式:让 AI 开口说话

### 4.1 不流式的等待:光标转了 40 秒

非流式请求的行为很「传统」:发出去,等,等到模型把整篇回答生成完,一次性把 JSON 返回。生成一篇长文要几十秒——这几十秒里用户盯着光标转圈,体验约等于 2002 年拨号上网。

流式(streaming)就是把这个过程拆开:请求发出后,**模型每生成一小段,服务端就立刻推给你一小段**,你边收边显示,打字机效果。用户看到的是「AI 在说话」而不是「AI 在发呆」——心理学上,等待的焦虑远大于打字的速度。

实现上两家一致:请求体加 `"stream": true`,响应不再是单个 JSON,而是一条 **SSE**(Server-Sent Events)流——就是普通的 HTTP 长连接,服务端不断吐 `data:` 开头的行。注意它**不是 WebSocket**:单向、无复杂握手、纯文本,curl 就能看。

### 4.2 SSE 拆帧:流里到底流着什么

先看 OpenAI 兼容格式的流(实测节选,`curl -N` 直连):

```
data: {"id":"1f13a6c8-...","object":"chat.completion.chunk","choices":[{"index":0,"delta":{"role":"assistant","content":"你"}}]}
data: {"id":"1f13a6c8-...","choices":[{"index":0,"delta":{"content":"好"}}]}
data: {"id":"1f13a6c8-...","choices":[{"index":0,"delta":{},"finish_reason":"stop"}}]}
data: [DONE]
```

OpenAI 系的流是「同构碎块」:每个 `data:` 行都是一个独立的 JSON(`object: "chat.completion.chunk"`),文字在 `choices[0].delta.content` 里逐字蹦出,最后一行 `data: [DONE]` 宣告结束。解析逻辑简单粗暴:**循环读行,遇到 `data: ` 就剥掉前缀 parse,`[DONE]` 就收工**。

再看 Anthropic 格式的流(同样实测节选),画风完全不同——它是**带事件类型**的:

```
event: message_start
data: {"type":"message_start","message":{"id":"cdc94224-...","usage":{"input_tokens":92,...}}}

event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你"}}

event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"好"}}

event: content_block_stop
data: {"type":"content_block_stop","index":0}

event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn"},"usage":{"output_tokens":17}}

event: message_stop
data: {"type":"message_stop"}
```

Anthropic 系把流组织成**事件序列**:`message_start` 先告诉你整条消息的骨架(id、输入 token 数),然后每个内容块(content block)经历 `start → delta… → stop`,文本增量在 `content_block_delta` 的 `delta.text` 里;全部块结束后 `message_delta` 补上 `stop_reason` 和输出 token 数,`message_stop` 收尾。

![流式:等全文 vs 打字机](fig-stream.svg)

两家的差异翻译成人话:OpenAI 的流是「同一份 JSON 被切成薄片端上来」,Anthropic 的流是「上菜报菜名」——每道菜端上来之前先广播一声「下一道是糖醋里脊」。用 SDK 时这些都被封装好了;裸写解析时,OpenAI 系认准 `delta.content`,Anthropic 系认准 `type == "content_block_delta" && delta.type == "text_delta"`。

> 一个小插曲:我实测时让模型「一句话介绍自己」,Anthropic 格式的流先推来一个 `type: "thinking"` 的块(模型在思考),然后才是 text 块。**如果你的前端只认 text 块,思考流会被当成噪音**——2026 年写流式解析,建议把「认识所有块类型、只挑你需要的」当成基本功。

### 4.3 流式里的用量:钱在哪一帧里

流式响应里没有集中的 `usage` 字段,用量信息藏在事件里:

- **Anthropic 系**:`message_start` 里带 `input_tokens`(输入是一次性算清的),`message_delta` 里逐段带 `output_tokens`(它是**增量**还是累计值各家实现略有差异——别假设,实测!)。要精确账单,把最后一条 `message_delta` 的数值取出来用。
- **OpenAI 系**:更抠门——**默认的流里根本没有 usage**,想要得在请求里加 `"stream_options": {"include_usage": true}`,然后最后一条 chunk(在 `[DONE]` 之前)会带上完整 `usage` 字段。

流式还有两个工程坑,提前打个预防针:

1. **超时**:非流式请求等 60 秒没回就是超时;流式请求只要还在吐字就不算超时——但也别把超时设成无穷大,模型卡住时(既不吐字也不报错)你得有个兜底。
2. **断流**:网络一抖,SSE 流可能半路断掉。断了怎么办?答案很朴素:**重新发一次请求**。API 没有「从断点续传」的协议,客户端能做的就是重试(第五章),配合前端「已显示的内容不重复」去重。

## 第五章 · 把调用做结实:生产环境见真章

demo 代码只要「能跑」,生产代码要「扛得住」。这一章把调用从玩具变成产品。

### 5.1 错误码一览:每种死法都有名字

两家 API 的错误都是标准 HTTP 状态码 + JSON 错误体,先背下这张表:

| 状态码 | 含义 | 常见原因 | 能重试吗 |
|---|---|---|---|
| 400 | 请求体不合法 | 缺字段、JSON 写错、参数非法 | 不能,改了再发 |
| 401 | 认证失败 | key 错、key 被吊销 | 不能 |
| 403 | 无权限 | key 没开通该模型/功能 | 不能 |
| 404 | 找不到 | **模型名拼错**(OpenAI/Anthropic 官方语义) | 不能 |
| 413 | 请求太大 | 输入超限 | 不能,得瘦身 |
| 429 | 限流 | 请求太密 / token 超配额 | **能**,按指示等 |
| 500 | 服务端出错 | 厂商内部故障 | **能**,退避重试 |
| 503/529 | 过载 | 服务忙不过来(Anthropic 独有 529) | **能** |

错误体两家都长这样(这是我实测的 401 和 400 真实返回):

```json
{"error": {"message": "Authentication Fails, Your api key: ****-123 is invalid",
           "type": "authentication_error"}}
```

```json
{"error": {"message": "The supported API model names are deepseek-v4-pro, deepseek-v4-flash, ... , but you passed no-such-model-xyz.",
           "type": "invalid_request_error"}}
```

规律一眼可见:`message` 给你人话,`type` 给程序用。调试第一法则:**先看状态码,再读 message,别瞎猜**。

有个容易踩的坑值得点名:模型名拼错时,OpenAI/Anthropic 官方返回 **404**(把模型 ID 当资源),而 DeepSeek 兼容层返回 **400**。所以「按状态码写死分支」的代码换厂商就失灵——这是兼容生态的必修课,第六章细说。另外 429 的响应头里藏着限流情报:`retry-after`(建议等几秒)和 `x-ratelimit-*` 系列(还剩多少额度),尊重它,别硬刚。

### 5.2 限流与退避重试:别当撞门的莽夫

第一次在生产环境遇到 429,新手的第一反应是「马上再发一次」——然后收到第二个 429,于是再发,再 429,像一只对着玻璃门反复起跳的鸟。

![退避重试:莽夫 vs 绅士](fig-retry.svg)

正确的姿势是**指数退避**:第一次失败等 1 秒重试,再失败等 2 秒、4 秒、8 秒……每次翻倍,并加一点随机抖动(免得一群客户端同步重试,把服务端撞得更惨——这叫惊群)。上限几次就该放弃报错,别重试到天荒地老。

要点一:**只重试「值得重试」的错误**。429/5xx/网络断开——重试;400/401/403——重试一万次结果一样,纯属烧钱。用 SDK 时这点基本免费:OpenAI 和 Anthropic 的官方 SDK 默认就会对 429 和 5xx 做指数退避重试(默认 2 次),你手写的裸 curl 反而要自己实现。

要点二:**重试会双重扣费**。模型生成没有事务:第一次请求可能其实已经生成完了,只是响应在回程路上丢了,你重试就再付一次钱。好在 LLM 调用幂等性足够好(同样的输入几乎同样的输出),重试的代价主要是钱而不是副作用——但也正因如此,「自动重试」和「账单监控」最好一起上。

要点三:Anthropic 的 529 是个体贴的设计——服务过载时用专门的 529(overloaded)而不是笼统的 500,让你的重试逻辑能区分「我的错」和「它的忙」。

### 5.3 超时与半截响应:世界的尽头是断网

生产环境第三课:请求会超时。SDK 通常有默认超时(Anthropic SDK 默认 10 分钟,还会按 `max_tokens` 自动放宽——因为长输出的生成确实要时间),手写 HTTP 记得自己设。

流式响应断在半路怎么办?回顾第四章的结论:**没有续传协议,重新发**。为了不重复显示,前端记住已收到的内容,重连后从断点继续拼;为了不重复干活,后端对「发出去的内容」做去重。简单粗暴,但这就是目前各家 API 的现实——流式是一个「尽力而为」的管道,不是可靠传输。

还有一类半截响应藏在 200 里:模型写一半撞上 `max_tokens` 上限,`finish_reason` 是 `max_tokens` 而不是正常结束。处理姿势:要么调大上限,要么检测到截断后,把已生成的内容作为 assistant 消息追加进历史,再发一次「继续」——模型会接着往下写。这个技巧在长文生成里几乎是必用的。

## 第六章 · 生态:一套代码跑遍所有大模型

### 6.1 OpenAI 兼容的秘密:换个 base_url 就走的原理

现在揭晓开头那个伏笔:为什么 DeepSeek 一个 key,能把第一章两个格式的示例都跑通?

因为 2026 年的 LLM API 生态有个不成文的共识:**OpenAI 的 chat/completions 格式是行业事实标准**。OpenAI 自己 2023 年定下的这套「messages 数组 + choices 响应」,被几乎所有后来者原样实现:DeepSeek、通义、智谱、Kimi、Ollama、vLLM……你甚至不用换 SDK——官方 `openai` Python 库支持自定义 `base_url`,改一行配置,同一套代码就从 OpenAI 官方切到任何兼容厂商:

```python
from openai import OpenAI

# OpenAI 官方
client = OpenAI(api_key="...")

# DeepSeek:只换 base_url,代码其余部分一字不动
client = OpenAI(api_key="...", base_url="https://api.deepseek.com")
```

![兼容生态:同一个 SDK,不同的底座](fig-eco.svg)

这套生态对开发者是天堂:今天用 A 家,明天嫌贵换 B 家,代码不动。对 OpenAI 则是「标准的诅咒」:它想推自己的新协议(Responses API,官方推荐新项目使用,语义化事件流、服务端状态管理),但全世界的兼容厂商都锚死在 chat/completions 上——事实标准一旦形成,不是官方发个推荐就能搬走的。

而 DeepSeek 走得更远:连 Anthropic 格式都兼容了——`base_url` 设成 `https://api.deepseek.com/anthropic`,就能用官方 `anthropic` SDK 直连。我实测跑通了,细节很有意思:

```
export ANTHROPIC_BASE_URL=https://api.deepseek.com/anthropic
export ANTHROPIC_API_KEY=sk-...
```

```python
import anthropic
client = anthropic.Anthropic()          # 自动读上面的环境变量
msg = client.messages.create(
    model="deepseek-v4-flash",
    max_tokens=1024,
    messages=[{"role": "user", "content": "你好"}],
)
```

**但「兼容」是约等于,不是等于。** 兼容层和官方之间,藏着各种微妙的差,全是我实测或查文档确认过的:

- **模型名自动映射**:在 DeepSeek 的 Anthropic 端点上写 `claude-opus-5`,它悄悄换成自家旗舰 `deepseek-v4-pro`;写 `claude-sonnet-5` / `claude-haiku-4-5`,换成 `deepseek-v4-flash`。你以为在点 Claude,实际吃的是 DeepSeek——接口兼容,大脑不同。
- **`anthropic-version` 头被忽略**:官方必带,DeepSeek 兼容层直接无视(带了也不报错)。「我按 2023 年的规矩来」这句对 DeepSeek 没有约束力。
- **`max_tokens` 可不填**:Anthropic 官方必填(缺了就 400),DeepSeek 兼容层实测不填照样 200——它比你想象的宽容。
- **模型名错误返回 400 而非 404**(第五章那个坑)。

所以对兼容层要有的正确心态:**协议兼容保你「能跑」,不保你「行为一致」**。换厂商前,把错误码语义、必填字段、模型能力差异都过一遍——大部分时候白捡便宜,少数时候踩坑,踩坑多半就踩在这些「约等于」上。

### 6.2 SDK 封装了什么:别重复造轮子

正文一路用 curl 教学,是为了让你看清协议。真要写产品,请直接上官方 SDK——它把四件事替你扛了:

1. **重试**:429/5xx 自动指数退避(默认 2 次),手写既啰嗦又容易写错;
2. **超时**:按模型和请求合理设置,长输出自动放宽;
3. **流式**:把 SSE 拆帧、事件解析封装成迭代器,你拿到的是「一段一段的文本」而不是 `data:` 原始行;
4. **类型与错误对象**:解析好的响应对象、分类好的异常(`RateLimitError`、`AuthenticationError`……),不用自己 parse JSON 和字符串匹配错误。

两份代码对照一下,差距立现。上面用 `curl` 写了 6 行才发出请求;用 SDK:

```python
import anthropic

client = anthropic.Anthropic()   # 读 ANTHROPIC_API_KEY / ANTHROPIC_BASE_URL
msg = client.messages.create(
    model="claude-sonnet-5",
    max_tokens=1024,
    system="你是资深职场助手",
    messages=[{"role": "user", "content": "帮我写一封请假邮件"}],
)
print(msg.content[0].text)       # 类型化对象,直接取文本
```

复杂场景(工具调用循环、流式进度、缓存标记)SDK 的价值还会翻倍。裸 curl 懂原理,SDK 干生产——两个都要会。

## 收尾:动手清单

看完不练等于没看,给你一份 20 分钟的自学路线,按顺序做一遍,LLM API 这关就算过了:

1. **申请 key**:任选一家(OpenAI 兼容的 DeepSeek/通义等都行,便宜大碗),`export 你的KEY变量=sk-...`;
2. **跑通第一章两条 curl**:OpenAI 格式一条、Anthropic 格式一条(DeepSeek 一个 key 全覆盖),看看 `usage` 字段,感受一下「一毛钱能问多少次」;
3. **把对话变多轮**:手动把 `assistant` 的回复拼回 `messages`,问它「我刚才说了什么」——亲身体会无状态 API 的记性;
4. **开流式**:给请求加 `"stream": true`,用 `curl -N` 看原始 SSE——然后换成 SDK 的流式接口,对比封装前后;
5. **故意犯错**:把 key 改错发一次(401)、把模型名拼错发一次(看 400 还是 404)、连续快速发 20 次(看会不会 429),每种死法亲眼见一次,比背十遍错误码表都管用;
6. **切一次厂商**:把 base_url 从一家切到另一家,跑通第六章那个「一字不改」的魔法——然后认真读新厂商的差异文档。

如果哪一步卡住,或者想让我把某个主题拆开写深(流式解析的边界情况?兼容层全对比?提示词缓存的实战调优?多轮会话的存储设计?),评论区说一声,我优先写它。

最后回到开场那句话:大模型不是魔法,是个 HTTP 接口。但接口背后,是真的在 GPU 上逐字思考的东西。理解了协议,你就站在了「会用」和「会造」的分界线上——剩下的,交给你的想象力,和你的账单。

