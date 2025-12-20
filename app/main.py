from fastapi import FastAPI
from . import models
from .db import engine
from .routers import ingest, summary, analysis

# This single line ensures that all tables derived from `Base` are created.
# It will create `indicator_thresholds` if it doesn't exist.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Healthcare AI API",
    description="API for ingesting, retrieving, and analyzing daily health and weather data.",
    version="0.4.0",
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Healthcare AI API"}

# Include routers
app.include_router(ingest.router)
app.include_router(summary.router)
app.include_router(analysis.router)
