# backend/tools/rag_tool.py

from rag.search import RAGSearcher
from rag.rag_services import RAGService
from rag.embeddings import load_embeddings

from langchain_chroma import Chroma


# ── Init vectorstore (singleton style) ───────────────────────────

CHROMA_PATH = "./chroma_db"

embeddings = load_embeddings(device="cpu")

vectorstore = Chroma(
    persist_directory=CHROMA_PATH,
    embedding_function=embeddings
)

searcher = RAGSearcher(vectorstore)
rag_service = RAGService(searcher)


# ── Main tool ────────────────────────────────────────────────────

def rag_tool(user_input: str, chat_history: list[dict] = None):
    """
    RAG Tool — handles both fresh queries and follow-up questions.

    Follow-up handling strategy:
    Instead of a brittle keyword detector, we always pass the last 3 messages
    of chat history into the RAGService prompt as context. The LLM inside
    RAGService naturally resolves pronouns and references ("it", "that policy",
    "the above") using the conversation context without any special detection logic.

    This means:
    - Fresh query with no history → works as before, history section is empty
    - Follow-up like "explain that further" → LLM sees previous exchange and resolves it
    - No false positives from keyword matching on words like "when", "who", "how"

    Args:
        user_input   : The RAG sub-task from the Copilot planner
        chat_history : Full conversation history from the session
    """

    chat_history = chat_history or []

    # Pass only the last 3 exchanges (6 messages) to keep the prompt focused
    recent_history = chat_history[-6:] if len(chat_history) > 6 else chat_history

    result = rag_service.answer(
        question=user_input,
        k=3,
        chat_history=recent_history         # passed through to RAGService prompt
    )

    return {
        "tool": "rag",
        "success": True,
        "answer": result["answer"],
        "citations": result["citations"],
        "context_used": user_input
    }