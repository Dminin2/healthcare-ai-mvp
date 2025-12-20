from fastapi import FastAPI
from . import models
from .db import engine
from .routers import ingest, summary, health

# This single line ensures that all tables derived from `Base` are created.
# SQLAlchemy is smart enough not to recreate existing tables.
# This will create the new tables: health_metric_raw, sleep_sessions, etc.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Healthcare AI API",
    description="API for ingesting and retrieving daily health and weather data.",
    version="0.2.0",
)

@app.get("/", tags=["Root"])
def read_root():
    return {"message": "Welcome to the Healthcare AI API"}

# Include routers
app.include_router(ingest.router, prefix="/ingest")
app.include_router(summary.router, prefix="/summary", tags=["Summary (Legacy)"])
app.include_router(health.router, prefix="/health_metrics")
