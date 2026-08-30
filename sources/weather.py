"""
M1 — Weather via Open-Meteo (no key required).

Fetches current conditions, today's high/low, and an hourly rain forecast for
any location. Temperatures returned in both °F and °C. Includes a plain-English
rain summary derived from hourly precipitation probability.
"""

import requests
from datetime import date, datetime

LOCATIONS = [
    {"name": "Evanston, IL", "lat": 42.0565, "lon": -87.6753, "timezone": "America/Chicago"},
    {"name": "Toronto, ON",  "lat": 43.6532, "lon": -79.3832, "timezone": "America/Toronto"},
]

WMO_CODES = {
    0: "Clear sky",
    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Fog", 48: "Icy fog",
    51: "Light drizzle", 53: "Drizzle", 55: "Heavy drizzle",
    61: "Light rain", 63: "Rain", 65: "Heavy rain",
    71: "Light snow", 73: "Snow", 75: "Heavy snow",
    77: "Snow grains",
    80: "Light showers", 81: "Showers", 82: "Heavy showers",
    85: "Snow showers", 86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail",
}

RAIN_THRESHOLD = 30  # % probability considered meaningful


def _to_c(f: float) -> int:
    return round((f - 32) * 5 / 9)


def _fmt_hour(iso_str: str) -> str:
    return datetime.fromisoformat(iso_str).strftime("%-I %p")


def _rain_summary(hourly_times: list, hourly_prob: list) -> str:
    rainy = [(t, p) for t, p in zip(hourly_times, hourly_prob) if p >= RAIN_THRESHOLD]
    if not rainy:
        return "No significant rain expected."
    peak = max(p for _, p in rainy)
    first, last = rainy[0][0], rainy[-1][0]
    if first == last:
        return f"Rain possible around {_fmt_hour(first)} (up to {peak}%)."
    return f"Rain likely {_fmt_hour(first)}–{_fmt_hour(last)} (peak {peak}%)."


def fetch_weather(lat: float, lon: float, location_name: str, timezone: str = "auto") -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": ["temperature_2m", "apparent_temperature", "weather_code", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "hourly": ["precipitation_probability"],
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": timezone,
        "forecast_days": 1,
    }

    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    data = resp.json()

    current = data["current"]
    daily = data["daily"]
    hourly = data["hourly"]

    temp_f = round(current["temperature_2m"])
    feels_f = round(current["apparent_temperature"])
    high_f = round(daily["temperature_2m_max"][0])
    low_f = round(daily["temperature_2m_min"][0])

    return {
        "location": location_name,
        "date": date.today().strftime("%A, %B %d"),
        "condition": WMO_CODES.get(current["weather_code"], f"Code {current['weather_code']}"),
        "temp_f": temp_f,
        "temp_c": _to_c(temp_f),
        "feels_like_f": feels_f,
        "feels_like_c": _to_c(feels_f),
        "wind_mph": round(current["wind_speed_10m"]),
        "high_f": high_f, "high_c": _to_c(high_f),
        "low_f": low_f,  "low_c": _to_c(low_f),
        "precip_in": round(daily["precipitation_sum"][0], 2),
        "rain_summary": _rain_summary(hourly["time"], hourly["precipitation_probability"]),
    }


def fetch_all_weather() -> list[dict]:
    return [fetch_weather(loc["lat"], loc["lon"], loc["name"], loc["timezone"]) for loc in LOCATIONS]


if __name__ == "__main__":
    for w in fetch_all_weather():
        print(f"\nWeather for {w['location']} — {w['date']}")
        print(f"  Condition : {w['condition']}")
        print(f"  Current   : {w['temp_f']}°F / {w['temp_c']}°C  (feels like {w['feels_like_f']}°F / {w['feels_like_c']}°C)")
        print(f"  High / Low: {w['high_f']}°F / {w['high_c']}°C  —  {w['low_f']}°F / {w['low_c']}°C")
        print(f"  Wind      : {w['wind_mph']} mph")
        print(f"  Precip    : {w['precip_in']} in")
        print(f"  Rain      : {w['rain_summary']}")
