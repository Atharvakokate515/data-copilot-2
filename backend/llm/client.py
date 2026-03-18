# backend/llm/client.py

from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from dotenv import load_dotenv
import os

load_dotenv()

model = HuggingFaceEndpoint(
    repo_id="meta-llama/Llama-3.3-70B-Instruct",
    max_new_tokens=512,     # was 100 — silently truncated SQL for any complex query
    do_sample=False,
    repetition_penalty=0.6,
)
llm = ChatHuggingFace(llm=model, verbose=True)


def generate_text(prompt: str) -> str:
    return llm.invoke(prompt)


if __name__ == "__main__":
    print(os.getenv("HUGGINGFACEHUB_API_TOKEN"))
    print("==="*30)
    test_prompt = "Write a short poem about AI in 2 lines."
    try:
        response = generate_text(test_prompt)
        print("Test prompt:", test_prompt)
        print("LLM response:", response)
    except Exception as e:
        print("Error while testing LLM client:", e)