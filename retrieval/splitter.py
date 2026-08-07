from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

CHUNK_SIZE = 500
CHUNNK_OVERLAP = 100

def split_documents(documents: list[Document]) -> list[Document]:
    """
    Split Documnets into overlapping chunks.
    
    Args:
        documents: List of Langchain Document objects.

    Returns:
        List of Langchain Document objects, each representing a chunk of the original documents.    
    """

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNNK_OVERLAP,
    )   

    chunks = text_splitter.split_documents(documents)

    return chunks 

if __name__ == "__main__":
    documents = [Document(page_content="Hello " * 300)]
    chunks = split_documents(documents)
    print(f"Number of chunks: {len(chunks)}")
