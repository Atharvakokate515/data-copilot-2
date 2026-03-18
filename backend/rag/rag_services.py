# rag/rag_service.py

class RAGService:

    def __init__(self, searcher, llm=None):
        self.searcher = searcher
        self.llm = llm

    def answer(self, question: str, k: int = 3, chat_history: list[dict] = None):

        results = self.searcher.search(question, k)

        context = "\n\n".join(
            f"[{r['rank']}] {r['content']}"
            for r in results
        )

        if self.llm:

            # Build conversation history string for follow-up awareness.
            # If no history, this section is simply omitted from the prompt.
            history_text = ""
            if chat_history:
                lines = []
                for msg in chat_history:
                    role = msg.get("role", "unknown").capitalize()
                    content = msg.get("content", "")
                    lines.append(f"{role}: {content}")
                history_text = (
                    "\n\nConversation History (for follow-up context):\n"
                    + "\n".join(lines)
                )

            prompt = f"""
You are an enterprise knowledge assistant.
Answer the question using ONLY the provided document context.
If the question is a follow-up, use the conversation history to understand what it refers to.
Do NOT hallucinate. If the context does not contain the answer, say so clearly.
{history_text}

Document Context:
{context}

Question: {question}

Answer:"""

            response = self.llm.invoke(prompt)

            answer = (
                response.content
                if hasattr(response, "content")
                else response
            )

        else:
            answer = results[0]["content"][:300] if results else "No results found."

        return {
            "answer": answer,
            "citations": results
        }