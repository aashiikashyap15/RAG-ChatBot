import google.generativeai as genai
from dotenv import load_dotenv
import os

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
_model = genai.GenerativeModel("gemini-2.5-flash-lite")


def build_prompt(query: str, chunks: list, history: list) -> str:
    context_parts = []
    for i, c in enumerate(chunks):
        m = c["metadata"]
        context_parts.append(
            f"[Chunk {i+1} | File: {m['source']} | "
            f"Page: {m['page']} | Index: {m['chunk_index']}]\n"
            f"{c['text']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    history_text = ""
    for msg in history[-6:]:
        role = "User" if msg["role"] == "user" else "Assistant"
        history_text += f"{role}: {msg['content']}\n"

    return f"""You are a helpful document assistant.
Answer using ONLY the context below.
If not found, say: "I couldn't find that in the uploaded documents."
Always mention source file and page number at the end.

=== CONTEXT ===
{context}

=== CONVERSATION HISTORY ===
{history_text}

=== USER QUESTION ===
{query}

Answer clearly and concisely:"""


def get_response(prompt: str) -> str:
    response = _model.generate_content(prompt)
    return response.text
