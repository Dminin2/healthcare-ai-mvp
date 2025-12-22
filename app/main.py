import os
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI
from . import models
from .db import engine
from .routers import ingest, summary, analysis, advice

def create_app():
    app = FastAPI(
        title="Healthcare AI API",
        description="API for ingesting, retrieving, analyzing, and generating advice from daily health and weather data.",
        version="0.5.0",
    )

    @app.get("/", tags=["Root"])
    def read_root():
        return {"message": "Welcome to the Healthcare AI API"}

    # Include routers
    app.include_router(ingest.router)
    app.include_router(summary.router)
    app.include_router(analysis.router)
    app.include_router(advice.router)

    return app

# Removed: app = create_app() # For normal application startup.
# This is now handled by uvicorn --factory option for production, and by conftest.py for testing.
