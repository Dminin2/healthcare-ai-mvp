import argparse
import requests
import sys
from datetime import date, datetime

OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

def fetch_weather_data(lat, lon, timezone):
    """Fetches weather data from the Open-Meteo API."""
    params = {
        "latitude": lat,
        "longitude": lon,
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
        "timezone": timezone,
    }
    try:
        response = requests.get(OPEN_METEO_API_URL, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from Open-Meteo: {e}", file=sys.stderr)
        sys.exit(1)

def post_to_ingest_api(base_url, weather_payload):
    """Posts the formatted weather data to the local ingest API."""
    ingest_url = f"{base_url.rstrip('/')}/ingest/weather"
    try:
        response = requests.post(ingest_url, json=weather_payload)
        response.raise_for_status()
        print("Successfully posted data to the API:")
        print(response.json())
    except requests.exceptions.RequestException as e:
        print(f"Error posting data to the ingest API at {ingest_url}: {e}", file=sys.stderr)
        print("Please ensure the FastAPI server is running.", file=sys.stderr)
        sys.exit(1)

def main():
    """Main function to parse arguments, fetch data, and post it."""
    parser = argparse.ArgumentParser(description="Fetch weather data from Open-Meteo and post it to the healthcare-ai API.")
    parser.add_argument("--date", help="The date to fetch data for in YYYY-MM-DD format. Defaults to today.", default=date.today().isoformat())
    parser.add_argument("--lat", type=float, default=-37.81, help="Latitude. Defaults to Melbourne.")
    parser.add_argument("--lon", type=float, default=144.96, help="Longitude. Defaults to Melbourne.")
    parser.add_argument("--timezone", default="Australia/Melbourne", help="Timezone. Defaults to Australia/Melbourne.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of the healthcare-ai API.")
    
    args = parser.parse_args()

    target_date_str = args.date
    try:
        # Validate date format
        datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Date format must be YYYY-MM-DD. Received: {target_date_str}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching weather data for {target_date_str}...")
    weather_data = fetch_weather_data(args.lat, args.lon, args.timezone)

    if not weather_data or "daily" not in weather_data:
        print("Error: Invalid or empty response from Open-Meteo API.", file=sys.stderr)
        sys.exit(1)

    daily_data = weather_data["daily"]
    try:
        date_index = daily_data["time"].index(target_date_str)
    except ValueError:
        print(f"Error: Date {target_date_str} not found in the API response.", file=sys.stderr)
        sys.exit(1)

    # Prepare the payload for our API
    payload = {
        "date": target_date_str,
        "temp_max": daily_data["temperature_2m_max"][date_index],
        "temp_min": daily_data["temperature_2m_min"][date_index],
        "precipitation_sum": daily_data["precipitation_sum"][date_index],
    }

    print(f"Found data: {payload}")
    post_to_ingest_api(args.base_url, payload)

if __name__ == "__main__":
    main()
