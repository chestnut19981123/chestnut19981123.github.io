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
