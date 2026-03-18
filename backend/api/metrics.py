# backend/api/metrics.py
"""
Observability layer.

Middleware : logs every request to request_logs table automatically.
Endpoint  : GET /api/metrics returns aggregated stats for a dashboard.
"""

import time
from fastapi import APIRouter, Request
from sqlalchemy import func

from memory.db import SessionLocal
from memory.models import RequestLog

router = APIRouter()


# ─────────────────────────────────────────────────────────────────
# Middleware (registered in main.py via app.middleware)
# ─────────────────────────────────────────────────────────────────

async def log_request_middleware(request: Request, call_next):
    """
    Logs latency + outcome for every API call.
    Skips /health and swagger routes to avoid noise.
    """
    skip = {"/health", "/docs", "/openapi.json", "/redoc"}
    if request.url.path in skip:
        return await call_next(request)

    start = time.time()
    response = await call_next(request)
    latency_ms = round((time.time() - start) * 1000, 2)

    path = request.url.path
    if "chat-db" in path:
        pipeline = "nl2sql"
    elif "agent-chat" in path:
        pipeline = "copilot"
    else:
        pipeline = "other"

    db = SessionLocal()
    try:
        db.add(RequestLog(
            endpoint=path,
            pipeline=pipeline,
            latency_ms=latency_ms,
            success=response.status_code < 400,
        ))
        db.commit()
    except Exception:
        pass    # never let logging crash the response
    finally:
        db.close()

    return response


# ─────────────────────────────────────────────────────────────────
# Metrics endpoint
# ─────────────────────────────────────────────────────────────────

@router.get("/metrics")
def get_metrics():
    """
    Aggregated observability stats for both pipelines.

    {
      "total_requests": int,
      "success_rate": float,
      "avg_latency_ms": float,
      "retry_rate": float,
      "sql_error_rate": float,
      "by_pipeline": { "nl2sql": {...}, "copilot": {...} },
      "by_tool": { "nl2sql": int, "rag": int, ... },
      "by_query_type": { "SELECT": int, "UPDATE": int, ... },
      "recent_errors": [ {"endpoint", "sql_error", "created_at"}, ... ]
    }
    """
    db = SessionLocal()
    try:
        total = db.query(RequestLog).count()
        if total == 0:
            return {"total_requests": 0}

        success_count = db.query(RequestLog).filter(RequestLog.success == True).count()
        retry_count   = db.query(RequestLog).filter(RequestLog.was_retried == True).count()
        error_count   = db.query(RequestLog).filter(RequestLog.sql_error != None).count()
        avg_latency   = db.query(func.avg(RequestLog.latency_ms)).scalar() or 0

        by_pipeline = {}
        for pipeline in ["nl2sql", "copilot"]:
            rows  = db.query(RequestLog).filter(RequestLog.pipeline == pipeline)
            count = rows.count()
            if count:
                ok  = rows.filter(RequestLog.success == True).count()
                avg = db.query(func.avg(RequestLog.latency_ms))\
                        .filter(RequestLog.pipeline == pipeline).scalar() or 0
                by_pipeline[pipeline] = {
                    "count": count,
                    "avg_latency_ms": round(avg, 2),
                    "success_rate": round(ok / count, 3)
                }

        by_tool = {
            r[0]: r[1] for r in
            db.query(RequestLog.tool_used, func.count(RequestLog.id))
              .filter(RequestLog.tool_used != None)
              .group_by(RequestLog.tool_used).all()
        }

        by_query_type = {
            r[0]: r[1] for r in
            db.query(RequestLog.query_type, func.count(RequestLog.id))
              .filter(RequestLog.query_type != None)
              .group_by(RequestLog.query_type).all()
        }

        recent_errors = (
            db.query(RequestLog)
              .filter(RequestLog.sql_error != None)
              .order_by(RequestLog.created_at.desc())
              .limit(10).all()
        )

        return {
            "total_requests":  total,
            "success_rate":    round(success_count / total, 3),
            "avg_latency_ms":  round(avg_latency, 2),
            "retry_rate":      round(retry_count / total, 3),
            "sql_error_rate":  round(error_count / total, 3),
            "by_pipeline":     by_pipeline,
            "by_tool":         by_tool,
            "by_query_type":   by_query_type,
            "recent_errors": [
                {
                    "endpoint":   e.endpoint,
                    "sql_error":  e.sql_error,
                    "created_at": e.created_at.isoformat()
                }
                for e in recent_errors
            ]
        }
    finally:
        db.close()