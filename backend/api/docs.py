# backend/api/docs.py
"""
Document upload and management endpoints.

POST /api/upload-doc    → upload a single PDF, ingest it (or re-ingest if updated)
GET  /api/docs          → list all ingested documents
DELETE /api/docs/{source} → delete a document and all its chunks
"""

import os
import shutil
import tempfile

from fastapi import APIRouter, UploadFile, File, HTTPException

from rag.ingest import RAGIngestor
from rag.rag_db import SessionLocal
from rag.models import Chunk

router = APIRouter()

_ingestor = None


def get_ingestor() -> RAGIngestor:
    global _ingestor
    if _ingestor is None:
        _ingestor = RAGIngestor(chroma_path="./chroma_db")
    return _ingestor


@router.post("/upload-doc")
async def upload_doc(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    # Save temp file with the REAL filename so ingest_pdf picks it up correctly
    tmp_dir = tempfile.mkdtemp()
    tmp_path = os.path.join(tmp_dir, file.filename)   # ← key fix: use real filename

    try:
        with open(tmp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        ingestor = get_ingestor()
        result = ingestor.ingest_pdf(tmp_path)   # os.path.basename now returns real filename

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")

    finally:
        # Clean up temp dir
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        os.rmdir(tmp_dir)

    return {"success": True, **result}


@router.get("/docs")
def list_docs():
    session = SessionLocal()
    try:
        from sqlalchemy import func
        rows = (
            session.query(
                Chunk.source,
                func.count(Chunk.id).label("chunk_count"),
                func.min(Chunk.created_at).label("ingested_at"),
            )
            .group_by(Chunk.source)
            .order_by(func.min(Chunk.created_at).desc())
            .all()
        )
        return {
            "success": True,
            "documents": [
                {
                    "source": row.source,
                    "chunk_count": row.chunk_count,
                    "ingested_at": row.ingested_at.isoformat(),
                }
                for row in rows
            ],
        }
    finally:
        session.close()


@router.delete("/docs/{source}")
def delete_doc(source: str):
    ingestor = get_ingestor()
    if not ingestor.is_already_ingested(source):
        raise HTTPException(status_code=404, detail=f"Document '{source}' not found.")
    deleted_count = ingestor._delete_existing_chunks(source)
    return {"success": True, "source": source, "chunks_deleted": deleted_count}