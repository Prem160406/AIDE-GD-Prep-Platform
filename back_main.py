from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from supabase import Client, create_client

logger = logging.getLogger("aide.backend")
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))


# ------------------------------------------------------------
# Environment
# ------------------------------------------------------------
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
ADMIN_PIPELINE_TOKEN = os.getenv("ADMIN_PIPELINE_TOKEN", "").strip()
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY")

if not ADMIN_PIPELINE_TOKEN:
    raise RuntimeError("Missing ADMIN_PIPELINE_TOKEN")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(title="AIDE Backend", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


# ------------------------------------------------------------
# In-process lock
# Note: good as an interim improvement; not sufficient for multi-instance deployments
# ------------------------------------------------------------
_pipeline_lock = threading.Lock()
_pipeline_running = False


# ------------------------------------------------------------
# DTOs
# ------------------------------------------------------------
class TopicDTO(BaseModel):
    id: int | None = None
    title: str | None = None
    summary: str | None = None
    source: str | None = None
    source_url: str | None = None
    date: str | None = None
    score: float | None = None
    decision: str | None = None
    pipeline_version: str | None = None
    factual_freshness: str | None = None
    debate_balance: str | None = None
    public_impact: str | None = None


class TopicsResponse(BaseModel):
    topics: list[TopicDTO]
    total: int


class PipelineRunResponse(BaseModel):
    status: str = Field(..., examples=["started", "completed", "already_running"])
    message: str
    return_code: int | None = None


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def require_admin_token(authorization: str | None = Header(default=None)) -> None:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing admin authorization",
        )

    token = authorization.removeprefix("Bearer ").strip()
    if token != ADMIN_PIPELINE_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin authorization",
        )


def safe_float_score(value: Any) -> float | None:
    if value is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        logger.warning("Invalid weighted_score value encountered: %r", value)
        return None

    if numeric < 0:
        numeric = 0.0
    if numeric > 1:
        numeric = 1.0

    return round(numeric * 10, 1)


def shape_topic(row: dict[str, Any]) -> TopicDTO:
    return TopicDTO(
        id=row.get("id"),
        title=row.get("title"),
        summary=row.get("summary"),
        source=row.get("source_name"),
        source_url=row.get("source_url"),
        date=row.get("published"),
        score=safe_float_score(row.get("weighted_score")),
        decision=row.get("decision"),
        pipeline_version=row.get("pipeline_version"),
        factual_freshness=row.get("factual_freshness"),
        debate_balance=row.get("debate_balance"),
        public_impact=row.get("public_impact"),
    )


def latest_published_batch_id() -> str | None:
    try:
        response = (
            supabase.table("pipeline_runs")
            .select("batch_id,status")
            .eq("status", "completed")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            return None
        return rows[0].get("batch_id")
    except Exception:
        logger.exception("Failed to resolve latest published batch")
        return None


def fetch_topics_rows() -> list[dict[str, Any]]:
    batch_id = latest_published_batch_id()

    query = (
        supabase.table("topics")
        .select(
            "id,title,summary,source_name,source_url,published,weighted_score,"
            "decision,pipeline_version,factual_freshness,debate_balance,public_impact,"
            "created_at,batch_id"
        )
        .order("created_at", desc=True)
        .order("id", desc=True)
    )

    if batch_id:
        query = query.eq("batch_id", batch_id)

    response = query.execute()
    return response.data or []


# ------------------------------------------------------------
# Routes
# ------------------------------------------------------------
@app.get("/")
def home() -> dict[str, str]:
    return {"message": "AIDE Backend is healthy"}


@app.get("/api/topics", response_model=TopicsResponse)
def get_topics() -> TopicsResponse:
    try:
        rows = fetch_topics_rows()
        topics = [shape_topic(row) for row in rows]
        return TopicsResponse(topics=topics, total=len(topics))
    except Exception:
        logger.exception("Failed to fetch topics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch topics",
        )


@app.get("/api/topics/{topic_id}", response_model=TopicDTO)
def get_topic_by_id(topic_id: int) -> TopicDTO:
    try:
        response = (
            supabase.table("topics")
            .select(
                "id,title,summary,source_name,source_url,published,weighted_score,"
                "decision,pipeline_version,factual_freshness,debate_balance,public_impact"
            )
            .eq("id", topic_id)
            .limit(1)
            .execute()
        )
        rows = response.data or []
        if not rows:
            raise HTTPException(status_code=404, detail="Topic not found")
        return shape_topic(rows[0])
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to fetch topic id=%s", topic_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch topic",
        )


@app.post("/api/admin/run-pipeline", response_model=PipelineRunResponse)
def run_pipeline(_: None = Depends(require_admin_token)) -> PipelineRunResponse:
    global _pipeline_running

    if not _pipeline_lock.acquire(blocking=False):
        return PipelineRunResponse(
            status="already_running",
            message="Pipeline is already running",
        )

    _pipeline_running = True
    try:
        pipeline_path = Path(__file__).parent / "__main__.py"
        if not pipeline_path.exists():
            logger.error("Pipeline entrypoint not found: %s", pipeline_path)
            raise HTTPException(status_code=500, detail="Pipeline entrypoint missing")

        logger.info("Starting pipeline subprocess: %s", pipeline_path)
        result = subprocess.run(
            [sys.executable, str(pipeline_path)],
            capture_output=True,
            text=True,
            timeout=600,
            cwd=str(Path(__file__).parent),
        )

        if result.returncode != 0:
            logger.error("Pipeline failed. stderr=%s", result.stderr[:4000])
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Pipeline execution failed",
            )

        logger.info("Pipeline completed successfully")
        return PipelineRunResponse(
            status="completed",
            message="Pipeline completed successfully",
            return_code=result.returncode,
        )

    except subprocess.TimeoutExpired:
        logger.exception("Pipeline timed out")
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Pipeline timed out",
        )
    finally:
        _pipeline_running = False
        _pipeline_lock.release()