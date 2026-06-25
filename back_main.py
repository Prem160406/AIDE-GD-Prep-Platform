from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path
import os
import sys
import subprocess

# ---- Load environment variables ----
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "SUPABASE_URL / SUPABASE_KEY not found. Make sure your .env file "
        "sits next to main.py."
    )

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="AIDE Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# RESPONSE SHAPING
# ============================================================
# Real column          -> Frontend field
# title                -> title
# summary              -> summary
# source_name          -> source
# published            -> date
# weighted_score (0-1) -> score (0-10, rounded)
# decision             -> decision

def shape_topic(row: dict) -> dict:
    score = row.get("weighted_score")
    return {
        "id": row.get("id"),
        "title": row.get("title"),
        "summary": row.get("summary"),
        "source": row.get("source_name"),
        "source_url": row.get("source_url"),
        "date": row.get("published"),
        "score": round(score * 10, 1) if score is not None else None,
        "decision": row.get("decision"),
    }


# ============================================================
# ROUTES
# ============================================================

@app.get("/")
def home():
    return {"message": "AIDE Backend is connected to Supabase!"}


@app.get("/api/topics")
def get_topics():
    try:
        response = (
            supabase.table("topics")
            .select("*")
            .order("created_at", desc=True)
            .order("id", desc=True)
            .execute()
        )
        topics = [shape_topic(row) for row in response.data]
        return {"topics": topics, "total": len(topics)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/topics/{topic_id}")
def get_topic_by_id(topic_id: int):
    try:
        response = (
            supabase.table("topics")
            .select("*")
            .eq("id", topic_id)
            .execute()
        )
        if not response.data:
            raise HTTPException(status_code=404, detail="Topic not found")
        return shape_topic(response.data[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/run-pipeline")
def run_pipeline():
    try:
        pipeline_path = Path(__file__).parent / "__main__.py"
        result = subprocess.run(
            [sys.executable, str(pipeline_path)],
            capture_output=True,
            text=True,
            timeout=600
        )
        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)
        return {"message": "Pipeline complete"}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Pipeline timed out after 5 minutes")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))