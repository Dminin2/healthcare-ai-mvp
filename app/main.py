import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from . import models
from .db import engine
models.Base.metadata.create_all(bind=engine)
from .routers import ingest, summary, analysis, advice, auth, health

def create_app():
    app = FastAPI(
        title="Healthcare AI API",
        description="API for ingesting, retrieving, analyzing, and generating advice from daily health and weather data.",
        version="1.0.0",
    )

    @app.get("/", tags=["Root"])
    def read_root():
        return {"message": "Welcome to the Healthcare AI API"}

    # Include routers
    app.include_router(auth.router)
    app.include_router(health.router)
    app.include_router(ingest.router)
    app.include_router(summary.router)
    app.include_router(analysis.router)
    app.include_router(advice.router)

    # Serve React frontend from /ui (built output must exist at frontend/dist/)
    _dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "frontend", "dist")
    if os.path.isdir(_dist):
        app.mount("/ui", StaticFiles(directory=_dist, html=True), name="frontend")

    return app

# Removed: app = create_app() # For normal application startup.
# This is now handled by uvicorn --factory option for production, and by conftest.py for testing.
