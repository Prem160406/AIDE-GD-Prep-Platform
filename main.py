from fastapi import FastAPI, Query
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from typing import Optional

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI()

@app.get("/")
def home():
    return {"message": "AIDE Backend is running!"}

@app.get("/topics")
def get_topics(status: Optional[str] = Query(None)):
    query = supabase.table("topics").select("*")
    
    # Agar status query param diya hai toh filter karo
    if status:
        query = query.eq("status", status)
    
    response = query.execute()
    return {"topics": response.data}