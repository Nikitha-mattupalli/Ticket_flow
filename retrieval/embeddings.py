from langchain_huggingface import HuggingFaceEmbeddings
from agents.config.settings import EMBEDDING_MODEL

def get_embedding_model() -> HuggingFaceEmbeddings:
    """
    Load and return the embedding model.

    This function provides a single pace to configure the embedding model used throughout the RAG pipeline.
    """

    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs ={
            "device": "cpu"
        },
        encode_kwargs={
            "normalize_embeddings": True
        }
    )

    return embeddings