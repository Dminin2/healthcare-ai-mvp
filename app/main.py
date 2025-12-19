from fastapi import FastAPI
from . import models
from .db import engine
from .routers import ingest, summary

# Create all tables in the database on startup
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Healthcare AI API",
    description="API for ingesting and retrieving daily health and weather data.",
    version="0.1.0",
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Healthcare AI API"}

# Include routers
app.include_router(ingest.router, prefix="/ingest", tags=["Ingestion"])
app.include_router(summary.router, prefix="/summary", tags=["Summary"])