# backend/main.py

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from memory.db import init_db
from rag.rag_db import init_rag_db
from api.chat import router as chat_router
from api.docs import router as docs_router
from api.metrics import router as metrics_router, log_request_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before the app begins serving requests."""
    init_db()       # creates nl2sql + copilot chat tables
    init_rag_db()   # creates chunks + queries tables
    yield


app = FastAPI(
    title="Enterprise Data Copilot",
    description="NL2SQL + RAG Copilot backend",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ─────────────────────────────────────────────────────────────────
# Replace "*" with your deployed frontend origin in production,
# e.g. allow_origins=["https://your-app.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Request logging middleware ────────────────────────────────────────────
app.middleware("http")(log_request_middleware)

# ── Routers ──────────────────────────────────────────────────────────────
app.include_router(chat_router, prefix="/api")
app.include_router(docs_router, prefix="/api")
app.include_router(metrics_router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}