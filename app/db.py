from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

SQLALCHEMY_DATABASE_URL = "sqlite:///./healthcare_ai.db"

import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./healthcare_ai.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

from . import models
Base.metadata.create_all(bind=engine)
