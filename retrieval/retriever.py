from pathlib import Path

from retrieval.vector_store import load_vector_store


PROJECT_ROOT = Path(__file__).resolve().parent.parent
VECTOR_STORE_ROOT = PROJECT_ROOT / "vector_stores"


class KnowledgeRetriever:
    def __init__(self, domain: str, top_k: int = 3):
        self.domain = domain
        self.top_k = top_k

        vector_store_path = VECTOR_STORE_ROOT / f"{domain}_db"

        if not vector_store_path.exists():
            raise FileNotFoundError(
                f"Vector store not found: {vector_store_path}"
            )

        self.vector_store = load_vector_store(
            str(vector_store_path)
        )

        self.retriever = self.vector_store.as_retriever(
            search_kwargs={
                "k": self.top_k,
            }
        )

    def retrieve(
        self,
        subject: str,
        description: str,
    ) -> str:
        query = f"""
Subject: {subject}

Description: {description}
"""

        documents = self.retriever.invoke(query)

        if not documents:
            return ""

        context_parts = []

        for index, document in enumerate(documents, start=1):
            source = document.metadata.get("source", "unknown")

            context_parts.append(
                f"""
Document {index}
Source: {source}

{document.page_content}
"""
            )

        return "\n\n---\n\n".join(context_parts)