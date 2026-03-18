# rag/search.py

from .rag_db import SessionLocal
from .models import Query


class RAGSearcher:

    def __init__(self, vectorstore):
        self.vectorstore = vectorstore

    def search(self, query, k=5):

        results = self.vectorstore.similarity_search_with_score(query, k=k)

        # Log query
        session = SessionLocal()
        session.add(Query(query=query))
        session.commit()
        session.close()

        formatted = []

        for rank, (doc, score) in enumerate(results, 1):

            formatted.append({
                "rank": rank,
                "content": doc.page_content,
                "source": doc.metadata.get("source"),
                "page": doc.metadata.get("page"),
                "score": float(score)
            })

        return formatted
