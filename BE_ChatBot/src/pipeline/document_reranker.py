from __future__ import annotations

from langchain_core.documents import Document as LangChainDocument
from rerankers import Document as RerankerDocument
from rerankers import Reranker as build_reranker


class DocumentReranker:
    """
    Rerank LangChain Document = mot interface chung.
    Ho tro local HuggingFace cross-encoder va Cohere API qua thu vien rerankers (PyPI).
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
        Tao reranker that su tu thu vien rerankers theo provider da chon.
        HuggingFace chay local, Cohere goi API va bat buoc co COHERE_API_KEY.
        """
        if self.provider == "huggingface":
            kwargs = {"model_type": "cross-encoder"}

            if self.device:
                kwargs["device"] = self.device

            if self.cache_dir:
                kwargs["model_kwargs"] = {"cache_dir": self.cache_dir}
                kwargs["tokenizer_kwargs"] = {"cache_dir": self.cache_dir}
            return build_reranker(self.model_name, **kwargs)

        if not self.api_key:
            raise ValueError("COHERE_API_KEY duoc yeu cau khi RERANKER_PROVIDER=cohere")

        return build_reranker(
            self.model_name,
            model_type="cohere",
            api_provider="cohere",
            api_key=self.api_key,
        )

    def compress_documents(
        self,
        documents: list[LangChainDocument],
        query: str,
    ) -> list[LangChainDocument]:
        """
        Nhan danh sach LangChain Document, rerank theo query va tra ve Document goc.
        Viec map nguoc theo doc_id giu nguyen metadata cho _docs_to_places().
        """
        if not documents:
            return []

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
