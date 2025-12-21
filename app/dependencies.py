from .db import SessionLocal

def get_db():
    """
    Dependency function that provides a database session for each request.
    """
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()
