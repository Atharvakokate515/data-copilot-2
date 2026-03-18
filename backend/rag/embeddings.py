# rag/embeddings.py
#---------------------------------------------------------------
# depriciated
#`pip install -U `langchain-huggingface` and import as `from `langchain_huggingface import HuggingFaceEmbeddings``
#---------------------------------------------------------------------------------
from langchain_huggingface import HuggingFaceEmbeddings

def load_embeddings(device="cpu"):

    return HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en",   # Faster than MiniLM
        model_kwargs={"device": device}
    )
#Switch to "cuda" if GPU exists.