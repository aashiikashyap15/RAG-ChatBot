import re
from typing import List, Dict


def split_into_chunks(
    text: str,
    chunk_size: int = 200,
    source_name: str = "unknown"
) -> List[Dict]:

    parts = re.split(r'\[Page (\d+)\]', text)
    chunks = []
    chunk_id = 0
    current_page = 1

    for part in parts:
        part = part.strip()
        if part.isdigit():
            current_page = int(part)
            continue
        if not part:
            continue

        part = re.sub(r'\s+', ' ', part).strip()
        words = part.split()
        step = max(1, chunk_size - 20)

        for i in range(0, max(1, len(words)), step):
            chunk_words = words[i:i + chunk_size]
            if len(chunk_words) < 15:
                continue

            chunk_uid = (
                f"{source_name}_p{current_page}_c{chunk_id}"
            )
            chunks.append({
                "id": chunk_uid,
                "text": " ".join(chunk_words),
                "metadata": {
                    "source": source_name,
                    "page": current_page,
                    "chunk_index": chunk_id,
                    "word_count": len(chunk_words)
                }
            })
            chunk_id += 1

    return chunks
