# ============================================================
# LLM-ASSISTED GROUND TRUTH GENERATION
# Dùng LLM để label relevance tự động
# Không cần sửa — chỉ cần update config.py khi đổi domain
# ============================================================

import json
import os
import time
from typing import List

from dotenv import load_dotenv
from langchain_chroma import Chroma

from config import (
    PERSIST_DIRECTORY, COLLECTION_NAME, TOP_K_RETRIEVE,
    DOC_ID_FN, DOMAIN_DESCRIPTION, DOMAIN_LANGUAGE,
)
from src.core.base_embed_model import get_embedding_model
from src.core.base_llm_model import LLMProvider
from src.core.llm_container import get_llm

load_dotenv()


def _sample_queries_from_docs(vectorstore: Chroma, llm, n_queries: int) -> List[str]:
    all_docs = vectorstore.get(limit=30)
    sample_texts = all_docs["documents"][:10]
    combined = "\n\n---\n\n".join(sample_texts)

    prompt = f"""You are helping build an evaluation dataset for a RAG system about {DOMAIN_DESCRIPTION}.

Based on the following document excerpts, generate {n_queries} diverse, realistic user questions in {DOMAIN_LANGUAGE}.
Questions should vary in: specificity, topic coverage, and phrasing.

Documents:
{combined[:3000]}

Return ONLY a JSON array of strings. No explanation. Example:
["Question 1?", "Question 2?", ...]"""

    result = llm.invoke(prompt)
    text = result.content.strip()

    if "```" in text:
        text = text.split("```")[1]
        if text.startswith("json"):
            text = text[4:]
    return json.loads(text.strip())


def _label_relevance(query: str, doc_id: str, doc_text: str, llm) -> int:
    prompt = f"""Rate the relevance of this document to the query on a scale of 0-3.

Query: {query}

Document excerpt (first 400 chars):
{doc_text[:400]}

Relevance scale:
0 = Not relevant at all
1 = Slightly relevant, mentions topic tangentially
2 = Relevant, contains useful information
3 = Highly relevant, directly answers the query

Return ONLY a single integer (0, 1, 2, or 3). Nothing else."""

    result = llm.invoke(prompt)
    try:
        score = int(result.content.strip()[0])
        return max(0, min(3, score))
    except:
        return 0


def build_ground_truth(
    n_queries: int = 20,
    output_path: str = "eval/ground_truth.json",
    delay_seconds: float = 0.5,
):


    # ── Khai báo LLM tập trung 1 lần, truyền xuống các hàm ──
    llm_query_gen = get_llm(LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")), temperature=0.7)
    llm_label     = get_llm(LLMProvider(os.getenv("REWRITE_LLM_PROVIDER")), temperature=0.1)

    print("🔌 Kết nối ChromaDB...")
    embedding_model = get_embedding_model()
    vectorstore = Chroma(
        persist_directory=PERSIST_DIRECTORY,
        embedding_function=embedding_model,
        collection_name=COLLECTION_NAME,
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": TOP_K_RETRIEVE})

    print(f"📝 Sinh {n_queries} câu hỏi từ nội dung docs...")
    queries = _sample_queries_from_docs(vectorstore, llm_query_gen, n_queries)
    print(f"✅ Sinh được {len(queries)} queries")

    dataset = []

    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Query: {query[:60]}...")

        docs = retriever.invoke(query)

        relevant_doc_ids = []
        graded_relevance = {}

        for doc in docs:
            doc_id = DOC_ID_FN(doc.metadata)
            score  = _label_relevance(query, doc_id, doc.page_content, llm_label)

            graded_relevance[doc_id] = score
            if score >= 1:
                relevant_doc_ids.append(doc_id)

            time.sleep(delay_seconds)
            print(f"   score={score} | {doc_id[-40:]}")

        dataset.append({
            "query": query,
            "relevant_doc_ids": relevant_doc_ids,
            "graded_relevance": graded_relevance,
        })

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    n_with_relevant = sum(1 for d in dataset if d["relevant_doc_ids"])
    print(f"\n✅ Saved {len(dataset)} queries → {output_path}")
    print(f"   {n_with_relevant}/{len(dataset)} queries có ít nhất 1 relevant doc")
    return dataset


if __name__ == "__main__":
    build_ground_truth(n_queries=20)