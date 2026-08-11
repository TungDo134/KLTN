from __future__ import annotations

from langchain_core.documents import Document as LangChainDocument


class DocumentReranker:
    """
    Rerank LangChain Document = mot interface chung.
    Ho tro local HuggingFace cross-encoder va Cohere API truc tiep.
    """

    SUPPORTED_PROVIDERS = {"huggingface", "cohere"}

    def __init__(
        self,
        provider: str,
        model_name: str,
        top_n: int,
        api_key: str | None = None,
        device: str | None = None,
        cache_dir: str | None = None,
    ):
        """
        Khoi tao provider, model va top_n dung cho buoc rerank tai lieu.
        Provider duoc chon tu .env va can restart backend neu muon doi.
        """
        self.provider = provider.strip().lower()
        self.model_name = model_name
        self.top_n = top_n
        self.api_key = api_key
        self.device = device
        self.cache_dir = cache_dir

        if self.provider not in self.SUPPORTED_PROVIDERS:
            raise ValueError(
                f"Khong ho tro reranker provider: {self.provider}. "
                f"Dung mot trong cac provider sau: {sorted(self.SUPPORTED_PROVIDERS)}"
            )

        if self.top_n <= 0:
            raise ValueError("RERANKER_TOP_N phai lon hon 0")

        self._ranker = self._build_ranker()
        if self._ranker is None:
            raise RuntimeError("KHOI TAO RERANKER THAT BAI. Vui long kiem tra lai.")

    def _build_ranker(self):
        """
        Tao reranker theo provider da chon.
        HuggingFace chay local, Cohere goi API va bat buoc co COHERE_API_KEY.
        """
        if self.provider == "huggingface":
            import torch
            from rerankers import Reranker as build_reranker

            kwargs = {"model_type": "cross-encoder"}
            kwargs["device"] = self.device or (
                "cuda" if torch.cuda.is_available() else "cpu"
            )

            if self.cache_dir:
                kwargs["model_kwargs"] = {"cache_dir": self.cache_dir}
                kwargs["tokenizer_kwargs"] = {"cache_dir": self.cache_dir}
            return build_reranker(self.model_name, **kwargs)

        if not self.api_key:
            raise ValueError("COHERE_API_KEY duoc yeu cau khi RERANKER_PROVIDER=cohere")

        from cohere import ClientV2

        return ClientV2(api_key=self.api_key)

    def compress_documents(
        self,
        documents: list[LangChainDocument],
        query: str,
    ) -> list[LangChainDocument]:
        """
        Nhiều Document lấy từ Chroma/BM25
            - So sánh lại từng Document với câu hỏi
            - Sắp xếp theo độ liên quan
            - Giữ top-N Document

        Nhan danh sach LangChain Document, rerank theo query va tra ve Document goc.
        Viec map nguoc theo index/doc_id giu nguyen metadata cho _docs_to_places().
        """
        if not documents:
            return []

        if self.provider == "cohere":
            results = self._ranker.rerank(
                model=self.model_name,
                query=query,
                documents=[doc.page_content for doc in documents],
                top_n=min(self.top_n, len(documents)),
            )
            return [documents[result.index] for result in results.results]

        from rerankers import Document as RerankerDocument

        reranker_docs = [
            RerankerDocument(
                text=doc.page_content,
                doc_id=index,
            )
            for index, doc in enumerate(documents)
        ]

        results = self._ranker.rank(query=query, docs=reranker_docs)
        top_results = results.top_k(min(self.top_n, len(documents)))

        return [documents[int(result.document.doc_id)] for result in top_results]
