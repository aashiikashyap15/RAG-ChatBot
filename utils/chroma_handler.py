
from sqlalchemy import (
    create_engine, Column, String,
    Integer, Text, DateTime
)
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://raguser:ragpass123@localhost:5432/ragdb"
)

Base = declarative_base()
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


# ── Models ─────────────────────────────────────────────────

class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    id = Column(String, primary_key=True)
    text = Column(Text, nullable=False)
    source = Column(String, nullable=False)
    page = Column(Integer, default=1)
    chunk_index = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    embedding = Column(Vector(3072))
    created_at = Column(DateTime, default=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(80), unique=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# ── DB Init ────────────────────────────────────────────────

def init_db():
    from sqlalchemy import text
    with engine.connect() as conn:
        conn.execute(
            text("CREATE EXTENSION IF NOT EXISTS vector")
        )
        conn.commit()
    Base.metadata.create_all(engine)
    print("✅ PostgreSQL tables ready.")


# ── Chunk Storage ──────────────────────────────────────────

def store_chunks(chunks: list):
    """Store embedded chunks, skip duplicates."""
    session = Session()
    try:
        existing_ids = {
            row[0]
            for row in session.query(DocumentChunk.id).all()
        }
        new_rows = []
        for chunk in chunks:
            if chunk["id"] in existing_ids:
                continue
            new_rows.append(DocumentChunk(
                id=chunk["id"],
                text=chunk["text"],
                source=chunk["metadata"]["source"],
                page=chunk["metadata"]["page"],
                chunk_index=chunk["metadata"]["chunk_index"],
                word_count=chunk["metadata"]["word_count"],
                embedding=chunk["embedding"]
            ))
        if new_rows:
            session.bulk_save_objects(new_rows)
            session.commit()
            print(f"  ✅ Stored {len(new_rows)} new chunks.")
        else:
            print("  ⚠️ All chunks already exist, skipped.")
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


# ── Similarity Search ──────────────────────────────────────

def search_chunks(query_embedding: list, top_k: int = 5) -> list:
    """Cosine similarity search via pgvector."""
    session = Session()
    try:
        results = (
            session.query(DocumentChunk)
            .order_by(
                DocumentChunk.embedding.cosine_distance(
                    query_embedding
                )
            )
            .limit(top_k)
            .all()
        )
        return [
            {
                "text": r.text,
                "metadata": {
                    "source": r.source,
                    "page": r.page,
                    "chunk_index": r.chunk_index,
                }
            }
            for r in results
        ]
    finally:
        session.close()


# ── Helpers ────────────────────────────────────────────────

def get_all_sources() -> list:
    """All unique uploaded filenames."""
    session = Session()
    try:
        rows = (
            session.query(DocumentChunk.source)
            .distinct().all()
        )
        return [r[0] for r in rows]
    finally:
        session.close()


def get_user(username: str):
    session = Session()
    try:
        return session.query(User).filter_by(
            username=username
        ).first()
    finally:
        session.close()


def create_user(username: str, password_hash: str):
    session = Session()
    try:
        user = User(
            username=username,
            password_hash=password_hash
        )
        session.add(user)
        session.commit()
        return True
    except Exception:
        session.rollback()
        return False
    finally:
        session.close()
