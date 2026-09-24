---
title: Tool Calling 介绍：给只会说话的模型一双手
cover: cover.svg
categories: 'AI'
tags: ['AI', 'Tool Calling', 'LLM', 'Agent']
date: 2026-09-24
---

## 开场：只会动嘴的「嘴强王者」

先做一个小测试：9.11 和 9.9 哪个大？

这个问题放到前几年，不少大模型会自信地回答「9.11 大」，理由是小数点后 9.11 有两位数、9.9 只有一位数。听起来很有道理，可惜错了——它把 9.11 当成版本号在比。类似的翻车现场当时还有很多：让它算一笔折扣总价，它给你一个听起来合理、实际对不上的数字；让它查天气，它编一个像模像样的天气预报。如今主流模型大多能分清这个问题，但当年的段子还在流传。

有一件事始终没变：大模型依然「只会说话」。它没有手、没有眼睛、连计算器都没有。不接任何工具的话，它查不了天气、订不了机票、改不了代码，既不知道真实世界正在发生什么，也无法对世界做任何事。它就像一个把才华全长在嘴上的「嘴强王者」：嘴上头头是道，手里空空如也。

而且就算它想帮你干活，你也不敢让它直接动手：它没有权限概念，不知道哪些文件能碰、哪些操作要人点头；出了事也没人负责——它连手都没有，怎么负责？所以问题的关键不是模型聪不聪明，而是它天生只能输出文字。它缺的是一双「手」。这双手，就是 Tool Calling，也叫 Function Calling，中文常译为「工具调用」。

![嘴炮 vs 动手](fig-vs.svg)

## 工具调用：一份外包合同

### 定义：模型只下单，不掌勺

Tool Calling 不是模型学会了用工具，而是模型学会了「下单」。

拿点外卖打比方：你是食客，模型是帮你打电话的外卖员，宿主是外卖平台，工具是后厨。外卖员不会做菜，也不知道后厨的菜谱，它只负责把订单递过去，等菜做好再端回来给你。Tool Calling 里的模型，就是那个只动嘴的外卖员。

具体到请求，你问模型「上海今天适合带伞吗」，它不会真的去查天气，但会输出一段结构化的「请求单」（为方便阅读，这里把 `arguments` 写成对象；真实格式是字符串化的 JSON，调用过程一章会看到）：

```json
{
  "name": "get_weather",
  "arguments": { "city": "上海" }
}
```

这段请求单有三个关键词：

- 结构化：它是机器可读的 JSON，不是「麻烦查一下上海的天气」这种自然语言，宿主拿到手就能解析、能校验。
- 可执行：请求单上的 `name` 和 `arguments` 对应一个真实存在的工具和一组参数，宿主照着就能调。
- 可回填：执行结果要作为新消息喂回模型，模型才能继续推理。只有请求、没有回填，调用就断在半路。

一句话版本：模型负责说清「要什么」，宿主负责把它变成「做了什么」。

### 环节：六个环节的接力

一次 Tool Calling 看着复杂，拆开就是六个环节：

| 环节 | 谁在做 | 干什么 |
| --- | --- | --- |
| 用户提问 | 用户 | 把问题发给模型 |
| 模型下单 | 模型 | 判断需要外部信息，输出调用请求 |
| 宿主执行 | 宿主 | 解析、校验，真的调用工具 |
| 工具返回 | 工具 | 把真实结果交回宿主 |
| 结果回填 | 宿主 | 把结果作为消息喂回模型 |
| 模型回答 | 模型 | 看完结果给出最终答案 |

注意最后两个环节的顺序不能反：一定是先把结果回填给模型，模型才组织回答。如果宿主把结果直接甩给用户、绕过模型，模型就失去了「看到结果、再判断」的机会，后面想继续调用别的工具也接不上。这也是 Tool Calling 和普通 API 调用最不一样的地方：它不是一次性的请求响应，而是一轮可以接下一轮的对话闭环。

说穿了不值钱，但它让一个只会输出文字的模型，获得了触达真实世界的能力。

### 权力：建议权与执行权

整个过程里有两个角色，权力完全不同：

- 模型有建议权：决定要不要调、调哪个、传什么参数。
- 宿主有执行权：决定调用合不合法、要不要执行、结果怎么处理。

这个分离是 Tool Calling 最值钱的设计。模型就算发疯想删库，宿主在执行前也能拦下来，或者弹窗问你一句「真的要删吗」。权限、安全和审计，都落在宿主这一侧，而不是交给一个只会猜字的模型。

那么工具从哪来？只要宿主有办法执行，几乎任何东西都能变成工具：

| 工具类型 | 例子 | 执行方式 |
| --- | --- | --- |
| 纯函数 | 数学计算、字符串处理 | 宿主本地直接算 |
| 数据查询 | 查数据库、查文件 | 宿主连数据库或读文件 |
| 外部 API | 天气、翻译、支付 | 宿主发 HTTP 请求 |
| 系统命令 | 跑测试、部署 | 宿主开子进程 |
| 界面操作 | 点按钮、填表单 | 宿主驱动浏览器 |

工具是什么形态不重要，重要的是它给模型开了一扇窗，让模型能「借助别人的手」做事。模型负责判断，宿主负责动手，工具负责出活，三者各管一段。

![说与做的分工](fig-concept.svg)

## 调用过程：四步走完一轮

### 前半：声明工具与模型点单

第一步是声明工具。开发者写一张工具名片（JSON Schema），宿主把名片连同用户问题一起发给模型。请求体长这样：

```json
{
  "model": "deepseek-flash",
  "messages": [
    { "role": "user", "content": "上海今天适合带伞吗？" }
  ],
  "tools": [ // 工具清单，就是递给模型的「菜单」
    {
      "type": "function",
      "function": {
        "name": "get_weather", // 工具名，模型靠它点名
        "description": "查询指定城市当天的天气，适合用户问下雨、温度、穿衣时调用", // 告诉模型什么时候用它
        "parameters": { // 参数格式
          "type": "object",
          "properties": {
            "city": { "type": "string", "description": "城市名，例如“上海”" }
          },
          "required": ["city"]
        }
      }
    }
  ]
}
```

和普通聊天请求相比，这里只多了一个 `tools` 字段，它就是递给模型的「菜单」。菜单里每个工具长这样：`type` 说明类型，`function` 里 `name` 是工具名，`description` 告诉模型什么时候用它，`parameters` 定义参数格式。

第二步是模型点单。模型看完菜单，认为需要查天气，于是不直接给出答案，而是先输出一段调用请求。返回的重点在 `message.tool_calls`，它是一个数组，里面每个元素是一次调用（教学版只保留关键字段）：

```json
{
  "model": "deepseek-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "我来查一下上海今天的天气。",
        "reasoning_content": "The user asks whether Shanghai needs an umbrella today. I should call get_weather for 上海.",
        "tool_calls": [
          {
            "index": 0,
            "id": "call_00_qJAAVoORsZa80B6L9u4p5367", // 回执编号，回填时必须对上
            "type": "function",
            "function": {
              "name": "get_weather", // 模型点名的工具
              "arguments": "{\"city\": \"上海\"}" // 字符串化的参数 JSON，宿主要先解析
            }
          }
        ]
      },
      "finish_reason": "tool_calls"
    }
  ]
}
```

<details>
<summary>参考：真实请求与完整返回</summary>

命令：

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-flash",
    "messages": [
      { "role": "user", "content": "上海今天适合带伞吗？" }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "查询指定城市当天的天气，适合用户问下雨、温度、穿衣时调用",
          "parameters": {
            "type": "object",
            "properties": {
              "city": { "type": "string", "description": "城市名，例如“上海”" }
            },
            "required": ["city"]
          }
        }
      }
    ]
  }'
```

返回：

```json
{
  "id": "8def9313-0de2-4eb0-99b3-482e08e78598",
  "object": "chat.completion",
  "created": 1790220004,
  "model": "deepseek-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "我来查一下上海今天的天气。",
        "reasoning_content": "The user asks whether Shanghai needs an umbrella today. I should call get_weather for 上海.",
        "tool_calls": [
          {
            "index": 0,
            "id": "call_00_qJAAVoORsZa80B6L9u4p5367",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\": \"上海\"}"
            }
          }
        ]
      },
      "logprobs": null,
      "finish_reason": "tool_calls"
    }
  ],
  "usage": {
    "prompt_tokens": 319,
    "completion_tokens": 65,
    "total_tokens": 384,
    "prompt_tokens_details": {
      "cached_tokens": 128
    },
    "completion_tokens_details": {
      "reasoning_tokens": 20
    },
    "prompt_cache_hit_tokens": 128,
    "prompt_cache_miss_tokens": 191
  },
  "system_fingerprint": "aeb56401ca74e127821c4f9126dcb669"
}
```

</details>

### 后半：宿主执行与结果回填

第三步是宿主执行。宿主解析参数、对照名片校验，然后真的去调天气接口。校验是最后一道闸门：模型可能把城市传成拼音、漏掉必填字段、甚至编一个不存在的参数，都靠宿主拦下。如果工具本身报错，宿主把错误信息原样回填，让模型换参数重试、换工具、或者如实放弃。

第四步是结果回填。宿主把结果作为一条 `tool` 消息喂回模型：

```json
{
  "model": "deepseek-flash",
  "messages": [
    { "role": "user", "content": "上海今天适合带伞吗？" },
    {
      "role": "assistant",
      "content": "我来查一下上海今天的天气。",
      "reasoning_content": "The user asks whether Shanghai needs an umbrella today. I should call get_weather for 上海.",
      "tool_calls": [
        {
          "index": 0,
          "id": "call_00_qJAAVoORsZa80B6L9u4p5367",
          "type": "function",
          "function": {
            "name": "get_weather",
            "arguments": "{\"city\": \"上海\"}"
          }
        }
      ]
    },
    {
      "role": "tool", // 消息类型：工具结果回填
      "tool_call_id": "call_00_qJAAVoORsZa80B6L9u4p5367", // 对上一步返回里的 id
      "content": "{\"city\": \"上海\", \"temp\": 28, \"sky\": \"晴\"}" // 执行结果，字符串化的 JSON
    }
  ],
  "tools": [
    {
      "type": "function",
      "function": {
        "name": "get_weather",
        "description": "查询指定城市当天的天气，适合用户问下雨、温度、穿衣时调用",
        "parameters": {
          "type": "object",
          "properties": {
            "city": { "type": "string", "description": "城市名，例如“上海”" }
          },
          "required": ["city"]
        }
      }
    }
  ]
}
```

模型看完结果，信息够了就直接回答，不够就继续调用别的工具，如此往复直到任务完成。最终回答长这样（简化版，完整返回在下面的折叠框里）：

```json
{
  "choices": [
    {
      "message": {
        "role": "assistant",
        "content": "上海今天不需要带伞（防雨）：天气晴，气温约 28℃，可以放心出门；紫外线较强，长时间在户外可以考虑带遮阳伞、涂防晒霜。", // 模型看完结果后的最终回答
        "reasoning_content": "Shanghai today: 28°C, sunny (晴). So no umbrella needed for rain. Let me answer. Maybe mention sun protection — an umbrella could be used for shade, but for rain, no need." // 思考过程
      }
    }
  ]
}
```

<details>
<summary>参考：真实请求与完整返回</summary>

命令（要点：assistant 消息原样回传，`reasoning_content` 和 `tool_calls` 都要带上，`tool_call_id` 与上一步一致）：

```bash
curl https://api.deepseek.com/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DEEPSEEK_API_KEY" \
  -d '{
    "model": "deepseek-flash",
    "messages": [
      { "role": "user", "content": "上海今天适合带伞吗？" },
      {
        "role": "assistant",
        "content": "我来查一下上海今天的天气。",
        "reasoning_content": "The user asks whether Shanghai needs an umbrella today. I should call get_weather for 上海.",
        "tool_calls": [
          {
            "index": 0,
            "id": "call_00_qJAAVoORsZa80B6L9u4p5367",
            "type": "function",
            "function": {
              "name": "get_weather",
              "arguments": "{\"city\": \"上海\"}"
            }
          }
        ]
      },
      {
        "role": "tool",
        "tool_call_id": "call_00_qJAAVoORsZa80B6L9u4p5367",
        "content": "{\"city\": \"上海\", \"temp\": 28, \"sky\": \"晴\"}"
      }
    ],
    "tools": [
      {
        "type": "function",
        "function": {
          "name": "get_weather",
          "description": "查询指定城市当天的天气，适合用户问下雨、温度、穿衣时调用",
          "parameters": {
            "type": "object",
            "properties": {
              "city": { "type": "string", "description": "城市名，例如“上海”" }
            },
            "required": ["city"]
          }
        }
      }
    ]
  }'
```

返回：

```json
{
  "id": "fdcf8b5c-7ed9-4754-ac31-903aadd29da8",
  "object": "chat.completion",
  "created": 1790220005,
  "model": "deepseek-flash",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "上海今天**不需要带伞（防雨）**：\n\n- 天气：晴 ☀️\n- 气温：28℃\n\n今天没有降雨，可以放心出门。不过 28℃ 的晴天紫外线可能较强，如果长时间在户外，可以考虑带把**遮阳伞**、涂防晒霜哦。",
        "reasoning_content": "Shanghai today: 28°C, sunny (晴). So no umbrella needed for rain. Let me answer. Maybe mention sun protection — an umbrella could be used for shade, but for rain, no need."
      },
      "logprobs": null,
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 414,
    "completion_tokens": 111,
    "total_tokens": 525,
    "prompt_tokens_details": {
      "cached_tokens": 256
    },
    "completion_tokens_details": {
      "reasoning_tokens": 44
    },
    "prompt_cache_hit_tokens": 256,
    "prompt_cache_miss_tokens": 158
  },
  "system_fingerprint": "aeb56401ca74e127821c4f9126dcb669"
}
```

</details>

### 翻车：三个常见场景

真实世界里最常见的翻车现场有三个：模型编参数（城市传成拼音）、工具本身出错（接口返回 500）、模型停不下来（一轮接一轮地调）。

成熟的做法分别对应：把参数约束写清楚并让宿主严格校验；把错误如实回填让模型重试或放弃；给循环设步数上限。这些都是宿主侧的工程问题，收尾还会再点一次。

![一次调用的完整往返](fig-trip.svg)

## 约束详解：给模型递一张看得懂的名片

### 全貌：一张完整的名片

工具清单里每个工具长什么样，由一张 JSON Schema 说了算。它是工具的「名片加体检单」：给模型看，决定它什么时候想起你、怎么点你；给宿主看，作为校验的尺子。先看一张完整名片，记住大框架：

![名片的解剖](fig-schema.svg)

整张名片只有两部分：上面是身份层（`name` 和 `description`），回答「你是谁、什么时候用你」；下面是参数层（`parameters`），回答「调用你要传什么参数」。下面两节分别拆这两层。

### 身份：name 与 description

身份层回答两个问题：模型怎么点名这个工具（`name`），以及什么时候该想起它（`description`）。两个键的用法如下：

| 键 | 作用 | 例子 |
| --- | --- | --- |
| `name` | 工具的唯一 ID，模型靠它点名 | 命名要一眼看懂用途：`get_weather`、`send_email` 都很好；`do_stuff` 就属于「看起来起了，其实没起」 |
| `description` | 决定模型什么时候用它，是名片里最值钱的部分 | 好写法三件事：适用场景（问下雨、温度、穿衣）、要传递的信息（城市、日期）、反例（文学、历史问题）。只写 `"weather tool"`，模型干脆不用；写成「用户问下雨、温度、穿衣时调用」，模型秒懂 |

### 参数：parameters 的规矩

参数层回答「调用工具时要传什么、怎么传」。结构固定：`parameters` 里的 `type` 是 `"object"`，参数永远是一个 JSON 对象；对象里用 `properties` 逐字段列约束。每个字段的约束有四个常用键：

| 键 | 作用 | 例子 |
| --- | --- | --- |
| `type` | 约束字段类型 | 常见取值见下方表格 |
| `description` | 告诉模型字段含义，最好带例子 | 写「城市名，例如“上海”」，模型照着抄；只写类型不写说明，模型可能传拼音 |
| `enum` | 焊死可选值 | `["today", "tomorrow"]`，写第三个直接打回 |
| `required` | 必填字段清单 | 缺了宿主直接报错，模型补上再试；可选字段留在外面 |

其中 `type` 是最常用的约束，常见取值和注意点如下：

| type | 含义 | 注意点 |
| --- | --- | --- |
| `string` | 文本 | 最常见；一定要配 `description` 给例子，否则模型可能传拼音、英文缩写 |
| `integer` | 整数 | 不接受小数；模型传 `"30"`（字符串）会被拦下，有些实现会先尝试转成数字，转不了才拒 |
| `number` | 数字，含小数 | 适合价格、比例这类可能带小数的值；字符串化的 `"3.5"` 同理会被拦下或先转换 |
| `boolean` | 布尔值 | 只收 `true` / `false`；模型传 `"yes"`、`1` 都会校验失败 |
| `array` | 数组 | 必须配 `items` 约束元素类型，否则模型可能塞进 `[123]` 或混合类型 |
| `object` | 嵌套对象 | 内部再写 `properties` 逐层约束；层级越深上下文越贵，能拍平就拍平 |

几个额外提醒：名片顶层和字段里各有一个 `description`——顶层那个管「什么时候用这个工具」，字段里那个管「这个参数是什么」，别混；`type` 别省略，写明确宿主校验才有依据；工具调用场景一般不用 `null` 类型，想表达「可以不传」就把它留在 `required` 之外；别依赖 `format`（如 `date-time`），各家实现支持不一，格式要求尽量写进 `description`。

字段还能嵌套：数组里套对象，对象里再约束字段。比如订餐时一份订单有多道菜：

```json
{
  "name": "order_food",
  "parameters": {
    "type": "object",
    "properties": {
      "items": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "name": {
              "type": "string",
              "description": "菜名，例如“宫保鸡丁”"
            },
            "count": {
              "type": "integer",
              "description": "份数"
            }
          },
          "required": ["name", "count"]
        }
      }
    },
    "required": ["items"]
  }
}
```

这里的层级是 `items`（数组）→ 每个元素（对象）→ `name` / `count`（字段）。模型能读懂这种嵌套，宿主也能一层层校验，还能防止模型往数组里塞不对类型的东西。

## 模型实现：从训练到推理

前面讲的是宿主怎么接住模型的请求，这一章换一个视角：模型凭什么会输出这种请求？

用一句话概括：Tool Calling 是训练出来的「输出格式」，不是学出来的「工具知识」。就像教实习生看菜单下单——重点不是他会做菜，而是他学会了「什么时候下单、怎么下单」。

### 训练：从预测文字到按格式下单

大模型的本职是预测下一个字：给它前半句，它续后半句，直到凑成一段话。这个阶段它只会「复述菜名」，完全不懂点单——你问它上海天气，它最多能「续写」一段像模像样的天气预报，因为它根本不知道世界上存在 get_weather 这回事。

要让它学会点单，靠的是指令微调（SFT）。人类准备大量训练样本，每个样本长这样：

```text
用户：上海明天会下雨吗？
工具清单：get_weather（查询指定城市当天的天气，参数 city）
正确答案：输出调用请求 { "name": "get_weather", "arguments": { "city": "上海" } }
```

样本三个部分缺一不可：用户问题决定触发条件，工具清单是模型唯一能见到的「菜谱」，正确调用示范教会模型「该下单时下单、该回答时回答」。训练数据主要来自两处：人工标注的高质量对话，以及用更强模型辅助生成、再人工筛过的合成数据。

经过大量这样的样本训练，模型学会了一件事：需要外部信息时，输出特定格式的调用请求，而不是硬编答案。注意，它学到的不是「会用 get_weather」，而是「会用 tool_use 这个格式说话」——它依然不知道天气接口怎么实现，甚至不知道这个接口存不存在，它只学会了「在这种输入下，输出那种格式」。

### 推理：菜单、约束与翻车

推理的时候，工具清单就是菜单。模型把用户问题和每个工具的 `description` 放在一起比对，看哪个最匹配意图就点哪个。它不知道工具怎么实现，只知道名片，就像菜单上不会写后厨的菜谱。工具少时，整份菜单直接塞进上下文；工具多时，光看菜单就占掉大量上下文，所以真实系统通常先做一轮工具筛选，只把相关的几张名片递给模型。

模型的输出本质是一串 token，如果让它自由发挥，可能输出「我想调一下天气接口，城市的话就上海吧」这种半成品。所以 API 侧有结构化解码（也叫约束解码）：生成时只允许符合格式的 token 出现，该出 `{` 的地方不能出别的，保证 `tool_calls` 一定是合法 JSON。实现上有两种思路：生成后解析（拿到结果再校验，失败就重试或报错）和生成中约束（边生成边卡格式，从根上杜绝非法输出，不少接口的 structured output 就是这么做）。模型输出看起来规整，不是它天生严谨，而是被格式约束住了。

模型自己也会翻车，而且原因和上一章不同：训练数据里只有文本示范，模型从没见过真实执行结果。从模型这一侧看，常见的翻车有四种：

| 翻车类型 | 表现 | 宿主对策 |
| --- | --- | --- |
| 编参数 | 把城市写成拼音、漏掉必填字段 | 对照名片严格校验，报错回填 |
| 选错工具 | 想查天气，调成了发邮件 | description 写具体，或先做工具筛选 |
| 报错不反思 | 收到「参数 city 不存在」还重复同样错误 | 报错信息写清楚，给模型可操作的提示 |
| 空转 | 明明能直接回答，也硬要调一次工具 | 降低调用倾向，允许模型直接回答 |

模型翻车不可怕，可怕的是没人拦、没人喂反馈。校验和回填，就是给模型装上的安全网。

### 进阶：带工具反馈的强化学习

既然模型没见过真实结果，那就让它见一见。很多 Agent 模型的后训练就是这样：让模型真的去调工具、看执行结果，再用强化学习调整它。具体做法是让模型在沙箱里「试调」：调用成功、结果有用，给正奖励；编参数、空转、把任务跑挂，给负奖励。模型从大量「试错 + 奖励」里学到什么调用值得做、什么调用是浪费。

经过这一步，调用准确率明显上升，编参数的毛病少很多，也更知道什么时候该停下来直接回答。工具越多、任务越复杂，这一步越重要——只靠 SFT 学格式的模型，在几十个工具面前会明显力不从心。

一句话总结：训练教它格式，菜单给它选择，宿主管验货，反馈让它越用越准。

![训练与推理双轨](fig-train.svg)

## 收尾：从「会说」到「会做」

单个工具调用是点一次菜；把调用放进「推理 → 执行 → 观察 → 再推理」的循环里，模型就能一口气完成查天气、订酒店、规划路线这类多步任务，每一步都用真实结果校正下一步——这就是 Agent 的核心。循环转起来之后，工具一多，宿主还要处理工具筛选、权限控制、并发管理、错误处理和步数上限这些工程问题；好在它们都是宿主侧的活，模型本身不用变，只要名片写得清楚、回填做得及时。

![单次调用 vs Agent 循环](fig-loop.svg)

回头看整篇文章的路线：开场那个 9.11 的翻车现场，暴露了模型「只会说话、没有手」的短板；接着我们拆开了 Tool Calling 这份外包合同，看了工具名片怎么写、模型怎么从训练到推理学会下单；最后把一次调用串成 Agent 循环，让它能一口气完成多步任务。

用一句话收尾：Tool Calling 是模型与真实世界之间的一份外包合同，模型负责说，宿主负责做，执行结果负责校正。

从「会说」到「会做」，差的不是魔法，而是一张写清楚的名片、一个严格验货的宿主，和一轮又一轮的执行循环。剩下的，就是动手给自己的模型接上这双手。
