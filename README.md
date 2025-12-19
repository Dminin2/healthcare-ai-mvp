# Healthcare AI API

This project provides an API to track correlations between daily health metrics, personal state, and weather data.

## API Server

### How to Run

1.  **Navigate to the project root:**
    ```bash
    cd /path/to/healthcare-ai/
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Activate your virtual environment (if you have one):**
    ```bash
    source .venv/bin/activate
    ```

4.  **Start the FastAPI application:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The application will be accessible at `http://127.0.0.1:8000`.

### API Documentation

While the application is running, you can access the interactive API documentation (Swagger UI) at:
*   `http://127.0.0.1:8000/docs`

This interface allows you to explore and test all API endpoints.

## Data Import Scripts

### Open-Meteo Weather Data

This script fetches historical weather data for a specific date from the Open-Meteo API and saves it to the database via the local API.

**Prerequisites:**
- The API server must be running.

**Execution Example:**

To fetch data for a specific date (e.g., December 20, 2025):
```bash
python scripts/import_open_meteo.py --date 2025-12-20
```

If the `--date` argument is omitted, it will fetch data for the current day. You can see all options with `python scripts/import_open_meteo.py --help`.

**Verification:**

After running the script, you can verify that the data was saved correctly:
1.  Go to the API documentation at `http://127.0.0.1:8000/docs`.
2.  Open the `GET /summary/last7d` endpoint in the "Summary" section.
3.  Click "Try it out" and then "Execute".
4.  Check the response body to ensure the weather data for the specified date has been populated.

