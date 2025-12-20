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

---

### Health Auto Export Ingestion

The `POST /ingest/health_metrics` endpoint is designed to receive JSON payloads directly from the Health Auto Export app.

**`curl` Example:**

You can simulate a payload POST using `curl`. Create a file named `sample-payload.json` with the content below, then run the command.

**`sample-payload.json`:**
```json
{
  "data": {
    "metrics": [
      {
        "name": "resting_heart_rate",
        "units": "count/min",
        "data": [{"date":"2025-12-19 00:23:00 +1100","qty":71}]
      },
      {
        "name": "sleep_analysis",
        "units": "hr",
        "data": [{
          "date":"2025-12-19 00:00:00 +1100",
          "sleepStart":"2025-12-19 02:07:17 +1100",
          "sleepEnd":"2025-12-19 09:11:47 +1100",
          "totalSleep":"6.91", "deep":"0.72", "core":"4.30", "rem":"1.88", "awake":"0.15"
        }]
      },
      {
        "name": "step_count",
        "units": "count",
        "data": [{"date":"2025-12-19 00:31:00 +1100","qty":"7403.4"}]
      }
    ]
  }
}
```

**`curl` Command:**
```bash
curl -X POST 'http://127.0.0.1:8000/ingest/health_metrics' \
-H 'Content-Type: application/json' \
-d @sample-payload.json
```

The API will respond with a JSON summary of the operation, e.g., `{"message":"Processing completed.","metrics_received":3,"records_inserted":3,"records_skipped":0,"warnings":[]}`.

### Getting Latest Health Summary

You can retrieve a summary of the most recent health data using the `GET /health_metrics/latest` endpoint.

```bash
curl -X GET 'http://127.0.0.1:8000/health_metrics/latest'
```

## Testing

The project includes a test suite using `pytest`.

**Prerequisites:**
- Ensure you have installed the development dependencies: `pip install -r requirements.txt`

**Running Tests:**

From the project root directory, run:
```bash
pytest
```
This will discover and run all tests in the `tests/` directory against a temporary test database (`test.db`).

