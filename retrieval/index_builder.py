from pathlib import Path
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_core.documents import Document
from langchain_chroma import Chroma
import shutil

from retrieval.splitter import split_documents
from retrieval.vector_store import create_vector_store


PROJECT_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_ROOT = PROJECT_ROOT / "knowledge"
VECTOR_STORE_ROOT = PROJECT_ROOT / "vector_stores"

def load_documents(domain: str) -> list[Document]:
    """
    Load documents from the specified domain directory.

    args:
        domain (str): The domain name corresponding to the directory containing the documents.

    returns:
        list[Document]: A list of Document objects loaded from the specified domain directory.    
    """

    knowledge_path = KNOWLEDGE_ROOT / domain

    if not knowledge_path.exists():
        raise FileNotFoundError(f"Domain directory '{knowledge_path}' does not exist.")

    loader = DirectoryLoader(knowledge_path, glob="**/*.md", loader_cls=TextLoader, loader_kwargs={"encoding": "utf-8"})

    documents = loader.load()

    if not documents:
        raise ValueError(f"No Markdown documents found in the domain directory '{knowledge_path}'.")

    for document in documents:
        document.metadata["domain"] = domain

    return documents


def build_index(domain: str, rebuild: bool = True) -> Chroma:
    vector_store_path = VECTOR_STORE_ROOT / f"{domain}_db"

    if rebuild and vector_store_path.exists():
        shutil.rmtree(vector_store_path)

    VECTOR_STORE_ROOT.mkdir(
        parents=True,
        exist_ok = True
    )      

    documents = load_documents(domain)
    chunks = split_documents(documents)

    if not chunks:
        raise ValueError(
            f"No chunks created for domain: {domain}"
        )

    vector_store = create_vector_store(
        documents=chunks,
        persist_directory=str(vector_store_path)
    )

if __name__ == "__main__":
    build_index("billing")    
