import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

client = chromadb.Client()

collections = {}



def store_chunks(session_id, chunks, embeddings):
    collection = client.get_or_create_collection(name=session_id)
    collections[session_id] = collection
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        collection.add(
            ids=[f"chunk_{i}"],
            embeddings=[embedding],
            documents=[chunk]
        )



def retrieve_chunks(session_id, query_embedding, top_k=3):
    collection = collections.get(session_id)
    if not collection:
        collection = client.get_collection(session_id)
    results = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    return results['documents'][0]
