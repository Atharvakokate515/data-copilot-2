# rag/ingest.py
"""
RAG ingestion pipeline with hybrid chunking strategy.

Chunking approach:
- Tries semantic/section-aware splitting first using markdown-style headers
  and double newlines as natural break points (works well for contracts,
  reports, policy docs that have real structure)
- Falls back to sentence-aware splitting (splits on ". " boundaries) for
  pages with no structural markers
- Fixed-size splitting only as last resort for dense unstructured text

This matters because:
- 500-char fixed splits break mid-sentence and destroy context in legal/financial docs
- Section-aware splits keep clauses and paragraphs intact → better retrieval
"""

import os
import re
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma

from .embeddings import load_embeddings
from .rag_db import SessionLocal
from .models import Chunk


# ── Chunking strategy ─────────────────────────────────────────────

# Primary: section-aware — respects headers, paragraphs, clauses
_SECTION_SPLITTER = RecursiveCharacterTextSplitter(
    separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "],
    chunk_size=600,
    chunk_overlap=80,
    length_function=len
)

# Fallback: sentence-aware for dense unstructured text 
_SENTENCE_SPLITTER = RecursiveCharacterTextSplitter(
    separators=[". ", "! ", "? ", "\n", " "],
    chunk_size=500,
    chunk_overlap=100,
    length_function=len
)


def _has_structure(text: str) -> bool:
    """
    Returns True if the page text has detectable structure:
    headers, numbered sections, double newlines, or bullet points.
    """
    return bool(re.search(r"(\n\n|\n[A-Z][^\n]{0,60}\n|\n\d+\.|•|-\s)", text))


def _chunk_page(text: str) -> list[str]:
    """
    Choose the right splitter per page based on content structure.
    Section-aware for structured docs, sentence-aware for dense prose.
    """
    if _has_structure(text):
        chunks = _SECTION_SPLITTER.split_text(text)
    else:
        chunks = _SENTENCE_SPLITTER.split_text(text)

    # Drop chunks that are too short to be useful (< 50 chars = likely noise)
    return [c.strip() for c in chunks if len(c.strip()) >= 50]


class RAGIngestor:

    def __init__(self, chroma_path="./chroma_db", device="cpu"):

        self.embeddings = load_embeddings(device)
        self.vectorstore = Chroma(
            persist_directory=chroma_path,
            embedding_function=self.embeddings
        )

    # ── Duplicate detection + cleanup ────────────────────────────

    def _get_existing_chroma_ids(self, source: str) -> list[str]:
        session = SessionLocal()
        try:
            rows = session.query(Chunk).filter(Chunk.source == source).all()
            return [row.chroma_id for row in rows]
        finally:
            session.close()

    def _delete_existing_chunks(self, source: str) -> int:
        existing_ids = self._get_existing_chroma_ids(source)
        if not existing_ids:
            return 0
        self.vectorstore.delete(ids=existing_ids)
        session = SessionLocal()
        try:
            session.query(Chunk).filter(Chunk.source == source).delete()
            session.commit()
        finally:
            session.close()
        return len(existing_ids)

    def is_already_ingested(self, source: str) -> bool:
        session = SessionLocal()
        try:
            return session.query(Chunk).filter(Chunk.source == source).first() is not None
        finally:
            session.close()

    # ── Page processor ────────────────────────────────────────────

    def _process_page(self, args):
        page_num, page = args
        text = page.extract_text()
        if not text:
            return []
        chunks = _chunk_page(text)
        return [(chunk, page_num) for chunk in chunks]

    # ── Ingest single PDF ─────────────────────────────────────────

    def ingest_pdf(self, pdf_path: str) -> dict:
        source = os.path.basename(pdf_path)
        is_update = self.is_already_ingested(source)

        deleted_count = 0
        if is_update:
            deleted_count = self._delete_existing_chunks(source)

        reader = PdfReader(pdf_path)
        texts, metadatas, ids = [], [], []
        timestamp = int(datetime.utcnow().timestamp())

        with ThreadPoolExecutor(max_workers=8) as executor:
            results = list(executor.map(self._process_page, enumerate(reader.pages)))
        
        chunk_counter = 0

        for page_chunks in results:
            for chunk, page_num in page_chunks:
                doc_id = f"{source}_{page_num}_{chunk_counter}_{timestamp}"
                texts.append(chunk)
                metadatas.append({"source": source, "page": page_num})
                ids.append(doc_id)
                chunk_counter += 1

        # After all chunks are collected
        if not texts:
            return {"source": source, "status": "empty", "chunks_added": 0}

        BATCH_SIZE = 128
        for i in range(0, len(texts), BATCH_SIZE):
            self.vectorstore.add_texts(
                texts=texts[i:i + BATCH_SIZE],
                metadatas=metadatas[i:i + BATCH_SIZE],
                ids=ids[i:i + BATCH_SIZE]
            )

        session = SessionLocal()
        try:
            for doc_id, meta in zip(ids, metadatas):
                session.add(Chunk(chroma_id=doc_id, source=meta["source"], page=meta["page"]))
            session.commit()
        finally:
            session.close()

        result = {
            "source": source,
            "status": "updated" if is_update else "ingested",
            "chunks_added": len(texts)
        }
        if is_update:
            result["chunks_deleted"] = deleted_count
        return result

    # ── Ingest folder ─────────────────────────────────────────────

    def ingest_folder(self, folder_path: str) -> list[dict]:
        results = []
        for file in os.listdir(folder_path):
            if file.endswith(".pdf"):
                results.append(self.ingest_pdf(os.path.join(folder_path, file)))
        return results