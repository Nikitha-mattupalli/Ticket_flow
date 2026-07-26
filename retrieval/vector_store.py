from langchain_chroma import Chroma
from langchain_core.documents import Document
from pathlib import Path
from retrieval.embeddings import get_embedding_model

def create_vector_store(documents: list[Document], persist_directory: str | Path) -> Chroma:
    """
    Create a Chroma vector store from the given documents and persist it to the specified directory.

    Args:
        documents (list[Document]): A list of Document objects to be stored in the vector store.
        persist_directory (str): The directory where the vector store will be persisted.

    Returns: Chroma vector store
    """

    embeddings = get_embedding_model()

    vector_store =  Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory
    )

    return vector_store


def load_vector_store(persist_directory: str) -> Chroma:
    """
    Load a Chroma vector store from the specified directory.

    Args:
        persist_directory (str): The directory where the vector store is persisted.
    Returns: Chroma vector store
    """

    embeddings = get_embedding_model()

    vector_store = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings
    )

    return vector_store
