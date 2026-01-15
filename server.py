import os
from fastapi import FastAPI, BackgroundTasks, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Import our pipeline functions
import scout
import enrich
import audit_agent
import dispatch
from main import run_pipeline

load_dotenv()

app = FastAPI(title="Radar de Reseñas IA - Backend")

# Enable CORS for the dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase Client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
API_KEY = os.getenv("API_KEY", "radar_secret_key_123")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_api_key(x_api_key: Optional[str] = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/health")
def health_check():
    return {
        "status": "online",
        "supabase": "connected" if supabase else "error",
        "langsmith": os.getenv("LANGCHAIN_TRACING_V2") == "true"
    }

@app.get("/stats")
def get_stats():
    try:
        res = supabase.table("leads").select("status").execute()
        data = res.data
        stats = {
            "total": len(data),
            "scouted": len([l for l in data if l["status"] == "scouted"]),
            "enriched": len([l for l in data if l["status"] == "enriched"]),
            "analyzed": len([l for l in data if l["status"] == "analyzed"]),
            "contacted": len([l for l in data if l["status"] == "contacted"]),
            "skipped": len([l for l in data if l["status"] == "skipped"]),
            "failed": len([l for l in data if l["status"] == "failed"])
        }
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/pipeline/run")
def trigger_pipeline(
    background_tasks: BackgroundTasks,
    niche: str = "gimnasios",
    city: str = "Mendoza, Argentina",
    limit: int = 10,
    x_api_key: Optional[str] = Header(None)
):
    verify_api_key(x_api_key)
    background_tasks.add_task(run_pipeline, niche, city, limit)
    return {"message": f"Pipeline started for {niche} in {city} (Limit: {limit})"}

@app.post("/pipeline/dispatch")
def trigger_dispatch(
    background_tasks: BackgroundTasks,
    limit: int = 50,
    x_api_key: Optional[str] = Header(None)
):
    verify_api_key(x_api_key)
    background_tasks.add_task(dispatch.dispatch_emails, limit)
    return {"message": f"Dispatch process started (Limit: {limit})"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
