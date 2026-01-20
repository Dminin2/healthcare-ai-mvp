# Health × Weather AI Advisor

A backend API that analyzes daily health metrics and weather data
to estimate personal health risk and generate daily health advice.

This project is designed as an MVP to explore how environmental factors,
such as weather conditions, can be combined with personal health data
to provide interpretable and actionable health insights.

---

## Overview

This service ingests daily weather data and personal health metrics,
evaluates health risk using rule-based logic,
and generates daily health advice using an LLM with fallback handling.

The project focuses on:
- Interpretability over black-box prediction
- Reproducible backend architecture
- Future extensibility toward preventive and emergency healthcare use cases

---

## Motivation

Many existing health applications focus on data visualization,
but do not clearly explain how external factors such as weather
affect daily physical condition.

This project aims to bridge that gap by:
- Explicitly modeling weather-related health risks
- Providing human-readable explanations and advice
- Serving as a foundation for future medical and healthcare AI systems

---

## Features

- Ingest daily weather data from Open-Meteo
- Ingest personal health metrics (e.g. heart rate, sleep, mood)
- Rule-based health risk evaluation (OK / Caution / Danger)
- AI-generated daily health advice with fallback logic
- Persistent storage of analysis and advice results
- Reuse stored advice to avoid redundant computation

---

## Architecture

Data flow:

1. Weather and health data are ingested via API endpoints
2. Analysis module evaluates daily health risk
3. Advice module generates personalized advice using an LLM
4. Results are stored in a database and reused when available

The system is implemented as a RESTful API using FastAPI.

---

## Tech Stack

### Backend
- Python 3.11
- FastAPI
- SQLAlchemy
- SQLite

### AI / Analysis
- Rule-based health risk evaluation
- Gemini API (LLM-based advice generation)

### External Services
- Open Meteo

### Infrastructure / Dev Tools
- Docker / Docker Compose
- pytest

---

## Supported Cities (Current)

For MVP simplicity, supported cities are currently defined statically in the code:

- Tokyo
- Melbourne
- Sydney
- Tasmania

This design choice allows rapid validation and experimentation.
Future versions will support dynamic configuration via config files,
database management, or user-defined locations.

---

## API Endpoints

- `POST /ingest/weather`
- `POST /ingest/health_metrics`
- `POST /ingest/daily_state`
- `GET  /summary/last7d`
- `GET  /analysis/{date}`
- `GET  /advice/{date}`

Detailed API documentation is available via Swagger UI.

---

## Run with Docker

### Requirements
- Docker
- Docker Compose

### Setup

Create a `.env` file in the project root and set required environment variables:

```
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```

### Run

```
docker compose up --build
```

The API will be available at: http://localhost:8000/docs

### Optional: Apple Watch + Cloudflare Setup

For personal use, this project supports real-time ingestion of Apple Watch
health data using:

- Apple Watch
- Health Auto Export (iOS)
- Cloudflare Tunnel

This setup allows health data to be sent from a mobile device
to a locally running server.

Note:
This configuration is optional and not required to evaluate or run the project.
The system can be fully tested using local or sample data.

---

## Roadmap

- Make supported cities configurable (config file or database)
- Build a web-based interface

This project focuses on designing a backend API that can serve as a foundation
for a future web-based interface.


---

## Disclaimer

This project is for educational and experimental purposes only.
It is not intended for medical diagnosis or treatment.
