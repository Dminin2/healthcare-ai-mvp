# Health×Weather AI MVP - Phase 1 (Foundation)

This project contains the foundational FastAPI application for the Health×Weather AI MVP.

## How to Run

1.  **Navigate to the project root:**
    ```bash
    cd /Users/Aoi/portfolio/healthcare-ai/
    ```

2.  **Activate your virtual environment:**
    ```bash
    source .venv/bin/activate
    ```
    (Or your specific venv activation command)

3.  **Start the FastAPI application:**
    ```bash
    uvicorn app.main:app --reload
    ```

    The application will be accessible at `http://127.0.0.1:8000`.

## Endpoints

*   `GET /`: Returns "ok"
*   `GET /health`: Returns `{"status": "ok"}`

## API Documentation

While the application is running, you can access the interactive API documentation (Swagger UI) at:

*   `http://127.0.0.1:8000/docs`
