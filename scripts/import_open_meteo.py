import argparse
import requests
import sys
from datetime import date, datetime

OPEN_METEO_API_URL = "https://api.open-meteo.com/v1/forecast"

LOCATIONS = {
    "melbourne": {"lat": -37.81, "lon": 144.96, "timezone": "Australia/Melbourne"},
    "tasmania":  {"lat": -42.8821, "lon": 147.3272, "timezone": "Australia/Hobart"},   # Hobart
    "sydney":    {"lat": -33.8688, "lon": 151.2093, "timezone": "Australia/Sydney"},
    "tokyo":     {"lat": 35.6762,  "lon": 139.6503, "timezone": "Asia/Tokyo"},
}

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
        raise RuntimeError(f"Error fetching data from Open-Meteo: {e}") from e

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
        raise RuntimeError(f"Error posting data to ingest API at {ingest_url}: {e}") from e

def import_weather_for_date(
    target_date_str: str,
    base_url: str = "http://127.0.0.1:8000",
    lat: float = -37.81,
    lon: float = 144.96,
    timezone: str = "Australia/Melbourne",
) -> dict:
    """Fetch -> pick target date -> post to ingest. Returns the posted payload."""
    # Validate date format
    datetime.strptime(target_date_str, "%Y-%m-%d")

    print(f"Fetching weather data for {target_date_str}...")
    weather_data = fetch_weather_data(lat, lon, timezone)

    if not weather_data or "daily" not in weather_data:
        raise RuntimeError("Invalid or empty response from Open-Meteo API.")

    daily_data = weather_data["daily"]
    try:
        date_index = daily_data["time"].index(target_date_str)
    except ValueError as e:
        raise RuntimeError(f"Date {target_date_str} not found in the API response.") from e

    payload = {
        "date": target_date_str,
        "temp_max": daily_data["temperature_2m_max"][date_index],
        "temp_min": daily_data["temperature_2m_min"][date_index],
        "precipitation_sum": daily_data["precipitation_sum"][date_index],
    }

    print(f"Found data: {payload}")
    post_to_ingest_api(base_url, payload)
    return payload

def main():
    """Main function to parse arguments, fetch data, and post it."""
    parser = argparse.ArgumentParser(description="Fetch weather data from Open-Meteo and post it to the healthcare-ai API.")
    parser.add_argument("--date", help="The date to fetch data for in YYYY-MM-DD format. Defaults to today.", default=date.today().isoformat())
    parser.add_argument("--lat", type=float, default=-37.81, help="Latitude. Defaults to Melbourne.")
    parser.add_argument("--lon", type=float, default=144.96, help="Longitude. Defaults to Melbourne.")
    parser.add_argument("--timezone", default="Australia/Melbourne", help="Timezone. Defaults to Australia/Melbourne.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="Base URL of the healthcare-ai API.")
    parser.add_argument("--location", choices=LOCATIONS.keys(), default="melbourne", help="Select a preset location (default: melbourne).",
)

    args = parser.parse_args()

    loc = LOCATIONS[args.location]
    args.lat = loc["lat"]
    args.lon = loc["lon"]
    args.timezone = loc["timezone"]

    print(f"Using location={args.location} lat={args.lat} lon={args.lon} tz={args.timezone}")

    target_date_str = args.date
    try:
        # Validate date format
        datetime.strptime(target_date_str, "%Y-%m-%d")
    except ValueError:
        print(f"Error: Date format must be YYYY-MM-DD. Received: {target_date_str}", file=sys.stderr)
        sys.exit(1)

    # print(f"Fetching weather data for {target_date_str}...")
    # weather_data = fetch_weather_data(args.lat, args.lon, args.timezone)

    # if not weather_data or "daily" not in weather_data:
    #     print("Error: Invalid or empty response from Open-Meteo API.", file=sys.stderr)
    #     sys.exit(1)

    # daily_data = weather_data["daily"]
    # try:
    #     date_index = daily_data["time"].index(target_date_str)
    # except ValueError:
    #     print(f"Error: Date {target_date_str} not found in the API response.", file=sys.stderr)
    #     sys.exit(1)

    # # Prepare the payload for our API
    # payload = {
    #     "date": target_date_str,
    #     "temp_max": daily_data["temperature_2m_max"][date_index],
    #     "temp_min": daily_data["temperature_2m_min"][date_index],
    #     "precipitation_sum": daily_data["precipitation_sum"][date_index],
    # }

    # print(f"Found data: {payload}")
    # post_to_ingest_api(args.base_url, payload)

    try:
        import_weather_for_date(
            target_date_str=target_date_str,
            base_url=args.base_url,
            lat=args.lat,
            lon=args.lon,
            timezone=args.timezone,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
