"""学知图谱 (LearnFlow) — AI Learning Agent Backend

Main FastAPI application entry point.
"""
import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle."""
    # Startup
    os.makedirs(Path(settings.upload_dir), exist_ok=True)
    os.makedirs(Path(settings.upload_dir) / "raw", exist_ok=True)
    os.makedirs(Path(settings.upload_dir) / "audio", exist_ok=True)
    os.makedirs(Path(settings.upload_dir) / "keyframes", exist_ok=True)

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    await init_db()
    print("✅ Database initialized")
    print(f"🚀 Server starting on http://localhost:8000")
    print(f"📝 API docs at http://localhost:8000/docs")
    yield
    # Shutdown
    print("👋 Server shutting down")


app = FastAPI(
    title="学知图谱 API",
    description="AI Learning Agent — Knowledge Graph Learning Assistant",
    version="0.1.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
upload_path = Path(settings.upload_dir)
upload_path.mkdir(exist_ok=True)
if upload_path.exists():
    app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

# Register routers
from routers import videos, notes, graph, qa
app.include_router(videos.router)
app.include_router(notes.router)
app.include_router(graph.router)
app.include_router(qa.router)


@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "version": "0.1.0",
        "llm_mode": settings.llm_mode,
        "llm_model": settings.llm_model
    }


@app.get("/")
async def root():
    return {
        "message": "学知图谱 API",
        "docs": "/docs",
        "health": "/api/health"
    }
