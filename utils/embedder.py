import time
import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def get_embedding(text: str) -> list:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_document"
    )
    return result["embedding"]


def get_query_embedding(text: str) -> list:
    result = genai.embed_content(
        model="models/gemini-embedding-001",
        content=text,
        task_type="retrieval_query"
    )
    return result["embedding"]


def batch_embed(chunks: list, delay: float = 0.15) -> list:
    total = len(chunks)
    for i, chunk in enumerate(chunks):
        chunk["embedding"] = get_embedding(chunk["text"])
        if (i + 1) % 5 == 0:
            print(f"  Embedded {i+1}/{total} chunks...")
        time.sleep(delay)
    print(f"  ✅ All {total} chunks embedded.")
    return chunks
