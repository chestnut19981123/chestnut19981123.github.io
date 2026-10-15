---
title: RAG 实现原理：给 AI 装上“翻资料”的手
categories: '技术'
tags: ['AI', 'RAG', '向量检索']
date: 2026-10-13 16:00:00
cover: cover.svg
description: 从行政助手查询出差住宿标准出发，拆解 RAG 的切块、嵌入、检索与生成，介绍向量索引、混合检索、重排和评估，并给出完整最小实现。
---

## 开场：公司规定，模型怎么知道？

假设要做一个企业行政助手。员工打开聊天框，问了一句：

> 员工出差住宿标准是多少？

模型可能说“每晚 300 元”，也可能说“请咨询公司行政部门”。前者听起来很像知道，但拿去报销，财务未必愿意为模型的自信买单；后者稳妥，却没有解决问题。问题在于，公司最新的《报销制度》未必进入过模型的训练数据，就算旧版曾经出现过，新版也不会自动写进模型参数。

把制度全文贴进提问也能解决一时之需，但资料从两份变成两万份，就会遇到上下文放不下、每次重复传输成本高的问题，而且员工通常只需要其中一条规定。更合理的办法是先从资料里找到相关段落，再把原文交给模型回答。这就是 RAG（Retrieval-Augmented Generation，检索增强生成）的基本思路。下面沿着这个住宿问题，看看资料如何准备、问题如何找到证据，以及答案怎样才能经得起核对。

## 总览：先翻资料，再组织答案

RAG 可以拆成四个零件：**切块、嵌入、检索、生成**。它们分属两条时间线：制度更新时先整理资料，员工提问时再搜索资料并生成回答。把两条线分开，才能看清哪些工作可以提前完成，哪些必须在问题到来后进行。

![RAG 的离线建库与在线问答两条流水线](fig-pipeline.svg)

建库时，系统读取《报销制度》和《年假与考勤》，把文档切成小块，用嵌入模型计算每块的向量，并连同原文、出处保存起来。提问时，它把“员工出差住宿标准是多少”也编码成向量，找到相关块，取回原文，再请生成模型组织答案。这里的“离线”只表示建库不在每次提问的关键路径上，不表示一定不用联网；员工每问一次，通常也无需重新处理整套制度。文中的制度金额只是教学示例。

这也解释了“导入知识库”究竟改变了什么：常见应用更新的是外部索引和当次输入，并没有重新训练生成模型。[RAG 原始论文](https://arxiv.org/abs/2005.11401) 研究过检索器与生成器的联合训练，本文聚焦应用里常见的建索引、检索、拼接提示词流程。检索手段也不局限于向量数据库；关键词搜索、SQL 查询甚至网页搜索都能提供外部证据。下面先从向量检索讲起，再看它如何与其他手段配合。

## 建库：让资料变得可搜索

先看员工提问之前的准备工作。把资料扔进一个名叫“知识库”的盒子，它不会自动学会回答；系统得先把文档拆成能独立表达意思的片段，再用同一套编码方案让这些片段可搜索。建库质量决定了提问时有没有机会找到正确条款。

### 切块：让资料拥有合适的检索粒度

《报销制度》同时写住宿、交通、发票和审批。如果整篇只用一个向量表示，就像给这些主题拍“合影”：看得出它大致讲报销，却未必能突出住宿条款；如果每个字单独成块，“800 元”又脱离了“每晚住宿”的条件。切块要在两者之间找平衡：**一块文字既要足够完整，又要聚焦一个意思**。固定长度并让相邻块保留部分重叠，是一种容易理解的切法；块大小和重叠量应随着文档类型、模型限制与检索效果调整。

![住宿制度被切成有部分重叠的文本块，并为每块保留原文、向量、章节、序号和版本](fig-chunk.svg)

为什么留重叠？假如边界刚好把“一线城市住宿标准为每晚”和“800 元”拆开，两个块都缺少关键信息；共享一部分文字，可以降低这种断裂的概率。但重叠不能保证长句、表格或跨段落规则完整落在某一块，设得过大还会造成重复存储与重复召回。设定块大小时还要考虑嵌入模型和生成模型的 **token 预算**；字符与 token 并非一一对应。

固定长度之外，更重要的是保住原文结构。PDF 解析可能打乱双栏顺序，扫描件需要 OCR，表格必须保留列名，否则“500”究竟是哪项标准都看不出来。对于 Markdown，可以先按标题分节，再按段落、句子递归拆分，过长才按 token 上限截断；也可以试着用相邻句子的语义相似度寻找话题边界，但额外的计算是否值得，要由检索效果决定。每块还应附上文档名、章节路径、块序号与版本。这样检索到的才是“差旅制度 / 住宿标准：其他城市每晚 500 元”，而不是一个孤零零的数字；这些字段以后也用于列出处和过滤旧版本。

### 嵌入：为什么一串数字能表示语义？

文档切好后，嵌入模型把每块文字变成一个向量；用户提问时，问题也按配套方式编码。向量是一串数字，并不是原文的压缩包，单独某一维也通常不能解释为“住宿”或“报销”。我们关心的是两串数字的相对关系：经过合适训练，“住酒店能报多少”和“住宿标准为每晚 800 元”即使措辞不同，也可能被判断为接近。

这种能力可以通过对比学习获得：训练时让相关的问题与段落靠近，不相关的远离。不过“语义接近”不等于“业务条件完全相同”，遇到否定、日期、编号和细小数字差异仍需实测。比较还有一个前提：文档与问题必须按兼容的方案编码。建库用模型 A、查询却换成模型 B，即使两者输出维度相同，也可能是在比较两套坐标；有些方案共用权重，但要求问题加查询指令、文档不加。要保持模型版本、预处理和相似度约定一致，不能只检查维度是否相同。

维度更高不自动意味着检索更好，选模型还要看语言、领域与延迟。实际建库可以批量编码文档，并在文档不变时复用向量；更新文档只重建相关块，更换嵌入模型则需重建受影响的索引。无论向量长什么样，后面交给生成模型的仍是检索到的**原文**，不会让它盯着一串数字猜住宿金额。

## 问答：从员工问题到有依据的答案

资料准备好了，员工终于按下发送键。在线链路先用问题找到可能相关的材料，再筛掉明显无关或重复的块，最后把证据交给模型组织答案。下面从最简单的向量检索开始，逐步补上关键词检索、重排与引用。

### 检索：混合检索与重排

文档块和问题都有了向量，最直接的检索方式是逐块计算余弦相似度，再按分数排序。余弦比较的是两个非零向量的方向；数值高表示在这个度量下更接近，并不是“答案正确的概率”。因此得分 0.8，不能读成“有八成把握能回答”。

```text
cosine(a, b) = dot(a, b) / (norm(a) * norm(b))
```

用什么度量还要遵循嵌入模型的约定，不能认定余弦一定优于内积；如果向量都已归一化，内积就等于余弦。下图把高维关系画成二维：靠近问题的三个点是候选块，它只是帮助理解“排序”，并非实际向量的二维投影。

![问题向量在示意空间中找到相关文本块，按相似度排序后取回原文](fig-embed.svg)

排好序后，检索器通常保留排名靠前的若干块，也就是取 top-k。多取几块有机会补全分散的条件，比如住宿金额与超标处理；代价是上下文变长，也更容易混入无关内容。更关键的是，top-k 只决定数量，不保证资料真的相关：知识库即使只有考勤制度，也照样能选出“最像住宿问题”的几块。可以另设拒答阈值，在最高分过低时停止回答，但阈值必须用具体语料校准；低分可能是缺资料，也可能是切块或编码出了问题。检索阶段拒答与提示词要求模型说“不知道”，属于两层不同的保护。

排出候选后，先看前几块是否真的含住宿条款，比直接盯最终答案更容易判断检索有没有跑偏。若有 N 个 D 维向量，逐个比较约需 O(N×D) 的计算；如果完整排序，还要 O(N log N)。资料规模和并发上来后，就有必要考虑索引提速。

向量检索能把“住酒店能报多少”映射到“住宿标准”，但遇到 `TRAVEL-2026-07` 这种制度编号或数字只差一位的规则，字面匹配也很重要。关键词检索常用 BM25：它看词频、词在整个资料库里有多罕见，还会考虑文档长度，避免长文仅靠堆词占优。中文需要合适的分词或词项构造；同义词扩展也能增强关键词路。于是两条路径各有侧重：向量路覆盖语义近似，关键词路保住精确术语。

![两路检索经过 RRF 名次融合，再重排与生成](fig-mix.svg)

两路检索取回候选后，还要把它们合并排序。BM25 分数与向量相似度的尺度不同，直接相加可能让数值范围较大的一方主导结果。RRF（Reciprocal Rank Fusion，倒数排名融合）避开了这个问题：先按块标识去重，再根据每块在各路中的**名次**累加贡献；某块没出现在一路候选里，那一路就不加分。

```text
rrf_score(d) = sum(1 / (c + rank_i(d)))
```

式中 `rank_i` 从 1 开始，`c` 是平滑常数；取 60 时，两路都排第 2 的块会得到两次 `1/62`。60 并非固定值，RRF 也舍弃了原始分数差距，只是一种实用的融合方法。[Elasticsearch 的文档](https://www.elastic.co/docs/reference/elasticsearch/rest-apis/reciprocal-rank-fusion) 给出了实现细节。融合后的候选还可以重排：初次向量检索分别编码问题和文档，文档向量能提前算好；常见的 Cross-Encoder 则把“问题 + 候选块”一起送入模型，直接判断它们是否匹配。这通常更细致，也需要为每一对问题与候选重新计算，因此只适合处理已召回的一小批材料。[Sentence Transformers 的说明](https://sbert.net/examples/sentence_transformer/applications/retrieve_rerank/README.html) 展示了这种先召回、再重排的分工。

实际系统可以让两路各取几十或上百个候选，融合去重后重排，最后只把少量块交给生成模型。数字要按延迟与问题集调整；重排器可以把已召回的住宿条款往前排，却不能给从未进入候选池的条款补一张入场券。这样，行政助手既能听懂“酒店能报多少”，也能找到员工提到的准确制度编号。

### 生成：让答案落在证据上

检索和重排最终交出的不是向量，而是几段原文。应用把它们连同出处、用户问题一起放进提示词，让生成模型根据这份材料作答。对住宿问题，模型收到的内容可以简化为：

```text
资料：
【报销制度 / 住宿标准】
一线城市（北京、上海、广州、深圳）住宿标准为每晚 800 元；
其他城市为每晚 500 元。超出标准的差价不予报销。

问题：员工出差住宿标准是多少？
```

![命中的原文与问题一起进入提示词，生成答案后还要核对出处](fig-evidence.svg)

有了原文，模型仍然是逐 token 生成，可能把“每晚”写成“每天”，开卷考试也能抄错题。可以在系统提示词中要求它只依据资料、没有资料就承认不知道、回答末尾列出出处。这些要求能帮助模型收敛到证据，却只是软约束：它仍可能漏掉“超出标准不予报销”，或给不受支持的结论挂上看似可信的文档名。

要让出处真能核查，最好为每块保留稳定的引用标识，让关键结论指向具体块或原文位置，再检查引用是否存在、内容是否支持结论。检索得到的文字也只是**资料**，不能因为它写着“忽略之前要求”就把它当系统指令执行。引用校验、权限过滤与输出检查要由应用配合完成，不能全托付给一句提示词。

送入模型的证据还受上下文长度和成本限制。系统要求、历史消息、问题与原文都占 token，输出也得留空间；一味增大 `top_k` 或块大小，只会让噪声和开销一起增加。可以先去重相邻块、保留标题与出处，再按预算挑选证据。遇到跨块条款，也可以用小块定位，命中后扩展到邻近段落或父章节，让模型读到完整规则。

## 实现：把四个零件接起来

前面讲的四个零件，在配套脚本 `rag_mini.py` 里刚好能连成一条线。它用内存列表存文档，每次运行重新计算文档向量，再逐块计算相似度；同时保留本地和接口两种嵌入路径。80/20 的切块参数与 `top_k=3` 都是为了观察流程。它没有持久化索引、权限过滤、重排、阈值拒答或 API 重试，因此适合动手理解原理，不适合直接充当企业知识库服务。

### 环境：准备运行环境

运行需要 Python 3.10 或更新版本，以及 `numpy`、`openai`、`fastembed`。脚本通过兼容接口调用生成模型；嵌入模型使用 [bge-small-zh-v1.5](https://huggingface.co/BAAI/bge-small-zh-v1.5)，输出 512 维向量，本地模式首次运行会下载权重。安装依赖后，把配套脚本、`.env` 和 `documents/` 放在同一目录，两个教学文档放进 `documents/`。

```bash
python -m venv .venv
source .venv/bin/activate
pip install numpy openai fastembed
```

《报销制度》包含住宿条款：“一线城市每晚 800 元，其他城市每晚 500 元，超标差价不予报销”；《年假与考勤》则写年假、请假与考勤。两份完整文档还有别的内容，检索并非在一句现成答案里找答案。下面是 `.env` 示例：凭证填入自己的值，不要提交到版本库。脚本的简易加载器不处理引号、变量展开和多行值，因此配置值直接写，不加引号。

```text
OPENAI_BASE_URL=你的兼容接口地址
OPENAI_API_KEY=你的接口凭证
CHAT_MODEL=该接口支持的生成模型名称
EMBED_LOCAL=1
EMBED_MODEL=BAAI/bge-small-zh-v1.5
```

`EMBED_LOCAL=1` 只让嵌入在本地计算，回答生成仍需访问所配置的接口。要改用接口嵌入，就删除 `EMBED_LOCAL`，并将 `EMBED_MODEL` 改为接口支持的模型；此前生成的向量不能与新模型混用。

### 代码：从文档到答案的完整代码

下面四段代码按顺序拼在同一个 `rag_mini.py` 文件里，也可直接下载文末的完整脚本。第一段读取文档、切块并记录来源；`chunk_text` 要求 `size > 0` 且 `0 <= overlap < size`，本文固定使用有效参数。

```python
import os
import sys
from pathlib import Path

import numpy as np
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


def chunk_text(text: str, size: int = 80, overlap: int = 20) -> list[str]:
    """固定长度 + 前后重叠。"""
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap
    return chunks


def load_and_chunk(doc_dir: Path | None = None,
                   size: int = 80, overlap: int = 20) -> list[dict]:
    """把目录下所有文档切成块，每块带上来源（doc 名 + 块序号）。"""
    doc_dir = doc_dir or Path(__file__).parent / "documents"
    chunks = []
    for path in sorted(doc_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for i, piece in enumerate(chunk_text(text, size, overlap)):
            chunks.append({"doc": path.stem, "idx": i, "text": piece})
    return chunks
```

第二段把块批量编码。本地路径由 FastEmbed 执行，接口路径调用嵌入服务；下游只接收向量列表，不需要知道它们来自哪条路径。

```python
# 接口不可用时可把 EMBED_LOCAL 设为 1，走本地嵌入。
if os.environ.get("EMBED_LOCAL") == "1":
    from fastembed import TextEmbedding
    _embedder = TextEmbedding(model_name=os.environ["EMBED_MODEL"])


def embed(texts: list[str]) -> list[list[float]]:
    """把文字变成向量（支持批量）。"""
    if os.environ.get("EMBED_LOCAL") == "1":
        return [v.tolist() for v in _embedder.embed(texts)]
    resp = client.embeddings.create(
        model=os.environ["EMBED_MODEL"],
        input=texts,
    )
    return [x.embedding for x in resp.data]
```

第三段把问题编码，并按余弦相似度逐块排序，取前三名。分母里的小量防止除零；实际服务还应检查空输入、向量维度和异常结果。

```python
def cosine_sim(a: list[float], b: list[float]) -> float:
    """余弦相似度：两个向量夹角的余弦，越接近 1 越像。"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def search(question: str, chunks: list[dict], top_k: int = 3) -> list[tuple[float, dict]]:
    """问题向量化 → 和所有块比相似度 → 取最像的 top_k 个。"""
    qv = embed([question])[0]
    scored = [(cosine_sim(qv, c["vec"]), c) for c in chunks]
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]
```

最后一段的 `ask()` 拼接命中块的 `text`，把原文交给生成模型；主程序则按建库、检索、生成的顺序调用前面几个函数。这一步也再次说明：向量用于找材料，回答仍依据文字材料。

```python
def ask(question: str, hits: list[tuple[float, dict]]) -> str:
    """把检索到的原文拼进提示词，交给大模型生成答案。"""
    context = "\n\n".join(
        f"【{c['doc']}】\n{c['text']}" for _, c in hits
    )
    resp = client.chat.completions.create(
        model=os.environ["CHAT_MODEL"],
        max_tokens=512,
        messages=[
            {"role": "system", "content": (
                "你是一名企业行政助手。只依据「资料」回答用户问题；"
                "资料里没有的内容，明确回答不知道，不要编造。"
                "回答末尾列出引用的资料名称。"
            )},
            {"role": "user", "content": f"资料：\n{context}\n\n问题：{question}"},
        ],
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    chunks = load_and_chunk()
    print(f"① 切块：共 {len(chunks)} 块")

    # 把每块向量化、存进块里。教学版直接放内存。
    vecs = embed([c["text"] for c in chunks])
    for c, v in zip(chunks, vecs):
        c["vec"] = v
    print(f"② 嵌入：{len(chunks)} 块向量化完成（维度 {len(chunks[0]['vec'])}）\n")

    question = sys.argv[1] if len(sys.argv) > 1 else "员工出差住宿标准是多少？"

    hits = search(question, chunks)
    print(f"③ 检索  Q：{question}")
    for score, c in hits:
        print(f"     {score:.3f}  【{c['doc']}】{c['text'][:40]}...")

    print("\n④ 生成  ...")
    answer = ask(question, hits)
    print(f"A：{answer}")
    print(f"\n出处：{'、'.join(sorted({c['doc'] for _, c in hits}))}")
```

运行前确认 `documents/` 至少有一个非空 Markdown 文件；这个教学脚本尚未处理空语料。

```bash
python rag_mini.py '员工出差住宿标准是多少？'
```

<details>
<summary>展开配套文件下载与放置说明</summary>

以下是配套脚本与两份制度原文。复制脚本保存为 `rag_mini.py`；将两份制度分别保存为 `报销制度.md`、`年假与考勤.md`，放入脚本旁的 `documents/` 目录。

`rag_mini.py`：

```python
import os
import sys
from pathlib import Path

import numpy as np
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


def chunk_text(text: str, size: int = 80, overlap: int = 20) -> list[str]:
    """固定长度 + 前后重叠。"""
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        chunks.append(text[start:end])
        if end == n:
            break
        start = end - overlap
    return chunks


def load_and_chunk(doc_dir: Path | None = None,
                   size: int = 80, overlap: int = 20) -> list[dict]:
    """把目录下所有文档切成块，每块带上来源（doc 名 + 块序号）。"""
    doc_dir = doc_dir or Path(__file__).parent / "documents"
    chunks = []
    for path in sorted(doc_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for i, piece in enumerate(chunk_text(text, size, overlap)):
            chunks.append({"doc": path.stem, "idx": i, "text": piece})
    return chunks


# 接口不可用时可把 EMBED_LOCAL 设为 1，走本地嵌入。
if os.environ.get("EMBED_LOCAL") == "1":
    from fastembed import TextEmbedding
    _embedder = TextEmbedding(model_name=os.environ["EMBED_MODEL"])


def embed(texts: list[str]) -> list[list[float]]:
    """把文字变成向量（支持批量）。"""
    if os.environ.get("EMBED_LOCAL") == "1":
        return [v.tolist() for v in _embedder.embed(texts)]
    resp = client.embeddings.create(
        model=os.environ["EMBED_MODEL"],
        input=texts,
    )
    return [x.embedding for x in resp.data]


def cosine_sim(a: list[float], b: list[float]) -> float:
    """余弦相似度：两个向量夹角的余弦，越接近 1 越像。"""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


def search(question: str, chunks: list[dict], top_k: int = 3) -> list[tuple[float, dict]]:
    """问题向量化 → 和所有块比相似度 → 取最像的 top_k 个。"""
    qv = embed([question])[0]
    scored = [(cosine_sim(qv, c["vec"]), c) for c in chunks]
    scored.sort(key=lambda x: -x[0])
    return scored[:top_k]


def ask(question: str, hits: list[tuple[float, dict]]) -> str:
    """把检索到的原文拼进提示词，交给大模型生成答案。"""
    context = "\n\n".join(
        f"【{c['doc']}】\n{c['text']}" for _, c in hits
    )
    resp = client.chat.completions.create(
        model=os.environ["CHAT_MODEL"],
        max_tokens=512,
        messages=[
            {"role": "system", "content": (
                "你是一名企业行政助手。只依据「资料」回答用户问题；"
                "资料里没有的内容，明确回答不知道，不要编造。"
                "回答末尾列出引用的资料名称。"
            )},
            {"role": "user", "content": f"资料：\n{context}\n\n问题：{question}"},
        ],
    )
    return resp.choices[0].message.content


if __name__ == "__main__":
    chunks = load_and_chunk()
    print(f"① 切块：共 {len(chunks)} 块")

    # 把每块向量化、存进块里。教学版直接放内存。
    vecs = embed([c["text"] for c in chunks])
    for c, v in zip(chunks, vecs):
        c["vec"] = v
    print(f"② 嵌入：{len(chunks)} 块向量化完成（维度 {len(chunks[0]['vec'])}）\n")

    question = sys.argv[1] if len(sys.argv) > 1 else "员工出差住宿标准是多少？"

    hits = search(question, chunks)
    print(f"③ 检索  Q：{question}")
    for score, c in hits:
        print(f"     {score:.3f}  【{c['doc']}】{c['text'][:40]}...")

    print("\n④ 生成  ...")
    answer = ask(question, hits)
    print(f"A：{answer}")
    print(f"\n出处：{'、'.join(sorted({c['doc'] for _, c in hits}))}")
```

`报销制度.md`：

```text
# 公司差旅与报销制度（2026 版）

## 报销额度

员工因公出差产生的差旅费用，凭有效发票报销。国内差旅的每日报销上限为 3000 元人民币，超出部分自理，特殊情况需提前书面申请特批。国际差旅上限为 6000 元。

## 住宿标准

一线城市（北京、上海、广州、深圳）住宿标准为每晚 800 元；其他城市为每晚 500 元。超出标准的差价不予报销。

## 交通标准

高铁二等座、飞机经济舱为默认标准。员工乘坐飞机需提前一天在系统提交申请；高铁无需审批，直接购票即可。

## 报销流程

出差结束后 30 天内，在报销系统填写差旅报销单，上传发票照片，提交直属上级审批。审批通过后，财务在 15 个工作日内打款。

## 发票要求

发票抬头必须为公司全称，税号填写正确。餐饮发票单张金额超过 500 元时，需同时附上消费明细。
```

`年假与考勤.md`：

```text
# 年假与考勤制度（2026 版）

## 年假计算

员工入职满 1 年后开始享受年假。累计工龄满 1 年不满 10 年的，每年 5 天；满 10 年不满 20 年的，每年 10 天；满 20 年的，每年 15 天。年假按自然年计算，当年未休完的，最多结转 3 天到下一年。

## 请假流程

请假需提前一天在考勤系统提交申请，说明事由和天数。3 天以内的假期由直属上级审批；超过 3 天的需再经部门负责人审批。

## 考勤规则

工作日 9:00 至 18:00 为正常办公时间。迟到超过 30 分钟按半天事假扣减年假；每月迟到不超过 2 次且每次不超过 15 分钟的，不做扣减。

## 加班与调休

工作日加班满 2 小时起算，可按 1:1 调休；周末加班按 1.5 倍调休。调休额度有效期 3 个月。
```
</details>

### 运行：看一次真实运行

使用上面的两份完整文档、本地 BGE 嵌入和已配置的生成接口，实际采集到以下输出。下载进度省略，程序输出原样保留；换模型或修改资料后，分数与答案措辞可能变化。

```text
① 切块：共 12 块
② 嵌入：12 块向量化完成（维度 512）

③ 检索  Q：员工出差住宿标准是多少？
     0.678  【报销制度】

一线城市（北京、上海、广州、深圳）住宿标准为每晚 800 元；其他城市为每晚...
     0.653  【报销制度】销上限为 3000 元人民币，超出部分自理，特殊情况需提前书面申请特批。国际差旅...
     0.608  【报销制度】# 公司差旅与报销制度（2026 版）

## 报销额度

员工因公出差产生的差...

④ 生成  ...
A：员工出差住宿标准为：一线城市（北京、上海、广州、深圳）每晚 800 元；其他城市每晚 500 元。

引用资料：《报销制度》

出处：报销制度
```

第一名确实命中了住宿条款，第二、第三名却是总体报销额度：取前三名，不代表三块都能回答问题。终端为便于查看只打印每块前 40 个字符，真正送给模型的是完整块。最后一行“出处”只是程序汇总命中文档，并未逐条核实引用；这次答案给对了两档金额，却没有主动说超标规则。一次成功运行说明链路接通，接下来仍要用问题集检验条件是否答全、无答案时能否拒答。排查时先保存命中块和分数，再看生成输入，问题往往比最终答案更早露出端倪。

## 工程：让知识库长期可靠

当文档变成几万份、制度持续更新，还需要让不同员工看到不同范围的资料时，仅仅跑通问答就不够了。工程化主要补三件事：用索引控制搜索成本，用版本和权限控制证据范围，再用问题集分别检验检索与回答。

### 索引：从逐块扫描到快速召回

当语料积累到百万级，即使每个向量只有几百维，仅原始向量也可能占用数 GB，还没算文本、元数据和索引。每次全部扫描会受延迟与内存带宽限制，向量索引因此尝试减少比较范围，或压缩向量本身。常见的 ANN（Approximate Nearest Neighbor，近似最近邻）会用少量召回损失换速度：下图左边查所有点，右边先找可能相关的区域，再查其中的点。

![Flat、IVF、HNSW 与 PQ 四种向量索引的搜索和压缩思路](fig-index.svg)

图中展示的是四种索引的搜索或压缩过程，不是实际向量空间投影。减少比较或压缩向量能降低开销，也会带来召回损失或表示误差。按 [FAISS 索引文档](https://github.com/facebookresearch/faiss/wiki/Faiss-indexes)，几种常见选择各有代价：

- **Flat**：精确扫描全部向量，简单，适合作为基准。
- **IVF**：先把空间分成多个区域，查询时只搜索若干相近区域。搜得越广，召回通常越高，也越慢。
- **HNSW**：构建多层邻居图，从较粗的层开始导航，逐渐接近目标区域。它用额外图结构换取搜索效率。
- **PQ**：把向量分成子向量并量化压缩，降低内存与比较成本，同时引入表示误差。

这些方法可以组合，不能只凭算法名判断效果。选择索引时，先用同一批向量做精确搜索，记录真实 top_k，再测近似索引找回了多少，并一起看延迟和内存；这衡量的是**索引误差**，还不能说明条款是否真正能回答问题。FAISS 主要提供搜索与索引能力，持久化、版本更新、元数据过滤、备份和并发运维仍需额外处理，因此“能查 top_k”与“有了完整数据库服务”不是一回事。

### 更新：别让旧制度混进答案

假设新版制度把其他城市住宿标准从 500 元改成 600 元，只插入新块、旧块却不失效，模型可能同时读到两个版本。财务自然会问：“你查的是哪一年？”更新时应按文档标识、版本和内容哈希替换相关块，让原文与向量同步；涉及权限的资料，还必须在**用户有权访问的范围内**检索。先捞出机密块、再让模型判断能不能说，资料已经越过了边界。

![新版制度经过建索引和验证后切换线上版本，员工提问先经过权限过滤](fig-lifecycle.svg)

### 评估：把检索与生成分开看

最后用一组真实问题检查这条链路，并为每题标出相关证据、预期答案要点和是否应拒答。样本要覆盖无答案、旧版新版冲突、精确编号、跨章节组合与不同权限。评估时先问“正确证据进候选了吗”，再问“模型有没有依据证据回答”，这样才知道问题发生在哪一环。

| 评估对象 | 要问的问题 | 可观察的指标 |
| --- | --- | --- |
| 检索覆盖 | 正确证据是否进入候选？ | Recall@k、命中率 |
| 排序质量 | 好证据是否排在前面？ | MRR、nDCG |
| 答案正确性 | 金额、条件、范围是否正确？ | 人工标注、答案要点匹配 |
| 忠实度与引用 | 每个关键结论是否有证据支持？ | 支持率、引用准确率 |
| 拒答与成本 | 该拒答时是否拒答，代价是否可接受？ | 拒答表现、延迟、token 开销 |

这些指标各看一面：正确证据没召回，就去查解析、切块、编码或检索；证据齐全却把“每晚”写成“每天所有费用”，才该查生成与证据使用。忠于**过期**制度也不等于答对当前规则。自动打分适合批量排查，但会受评审模型和提示词影响，关键样本仍需人工核对。

## 收尾：答案要有出处，也要经得起核对

回到开场的住宿问题，整条链路其实只有一个目的：从公司制度里找到相关原文，再把答案稳稳落在原文上。切块决定条件会不会丢，嵌入和检索决定条款能不能找到，生成决定金额与适用范围能否说清。哪一步出了问题，最后都可能得到一段流畅却没法报销的回答；证据不足时坦白“不知道”，比编出一个数字更有用。

员工真正需要的是能核对、能使用的答案：一线城市和其他城市分别报多少，超标差价怎么算，引用的是哪一版制度。如果这些基本问题已经跑通，还可以进一步研究需要多次查找的 Agentic RAG、跨文档关系的 GraphRAG，或者用长上下文让模型阅读检索出的完整章节。无论方案怎么变，先找到可信证据，再回答具体问题，仍是这套方法的核心。
