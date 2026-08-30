"""
M1 — Weather via Open-Meteo (no key required).

Fetches current conditions, today's high/low, and an hourly rain forecast for
any location. Temperatures returned in both °F and °C. Includes a plain-English
rain summary derived from hourly precipitation probability.
"""

import requests
from datetime import date, datetime

# Two locations are defined as plain dicts rather than a class — the data is
# simple enough that a dataclass or namedtuple would add boilerplate without
# improving readability. Each dict maps directly to the fetch_weather() parameters.
LOCATIONS = [
    {"name": "Evanston, IL", "lat": 42.0565, "lon": -87.6753, "timezone": "America/Chicago"},
    {"name": "Toronto, ON",  "lat": 43.6532, "lon": -79.3832, "timezone": "America/Toronto"},
]

# Open-Meteo uses WMO (World Meteorological Organization) standard weather codes.
# The API returns an integer (e.g. 63), not a string. This lookup table translates
# those integers into human-readable labels for the digest. Codes not in this dict
# fall back to "Code N" so the pipeline never crashes on an unknown value.
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

# Minimum hourly precipitation probability (%) to count as "meaningful rain."
# 30% is the conventional threshold used in weather forecasting — below this,
# most forecasters describe conditions as "dry" even if some chance exists.
RAIN_THRESHOLD = 30


def _to_c(f: float) -> int:
    # Standard F→C formula. We return int (rounded) because showing "22.2°C"
    # in a morning digest is unnecessary precision — the reader wants a feel
    # for the temperature, not lab accuracy.
    return round((f - 32) * 5 / 9)


def _fmt_hour(iso_str: str) -> str:
    # Open-Meteo returns hourly timestamps as ISO 8601 strings in the requested
    # timezone (e.g. "2026-08-29T14:00"). datetime.fromisoformat() parses this
    # without needing a format string. %-I gives hours without a leading zero
    # (platform-specific: works on macOS/Linux, not Windows).
    return datetime.fromisoformat(iso_str).strftime("%-I %p")


def _rain_summary(hourly_times: list, hourly_prob: list) -> str:
    # zip() pairs each timestamp with its probability, producing tuples like
    # ("2026-08-29T14:00", 45). The list comprehension filters to hours at or
    # above the threshold, giving us only the "rainy window."
    rainy = [(t, p) for t, p in zip(hourly_times, hourly_prob) if p >= RAIN_THRESHOLD]

    if not rainy:
        return "No significant rain expected."

    # max() with a generator expression — (p for _, p in rainy) — extracts just
    # the probability values without building an intermediate list. The underscore
    # is a convention for "I'm unpacking this tuple but don't need this element."
    peak = max(p for _, p in rainy)

    # First and last rainy hours define the window. If only one hour qualifies,
    # first == last and we phrase it as "around X" rather than "X–X."
    first, last = rainy[0][0], rainy[-1][0]
    if first == last:
        return f"Rain possible around {_fmt_hour(first)} (up to {peak}%)."
    return f"Rain likely {_fmt_hour(first)}–{_fmt_hour(last)} (peak {peak}%)."


def fetch_weather(lat: float, lon: float, location_name: str, timezone: str = "auto") -> dict:
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        # "current" gives a single snapshot for right now.
        # "daily" gives one aggregated value per day (used for high/low/precip).
        # "hourly" gives 24 values for each requested variable — one per hour of
        # the forecast window. We only request precipitation_probability here
        # because it's the only hourly value we need for the rain summary.
        "current": ["temperature_2m", "apparent_temperature", "weather_code", "wind_speed_10m"],
        "daily": ["temperature_2m_max", "temperature_2m_min", "precipitation_sum"],
        "hourly": ["precipitation_probability"],
        # Open-Meteo serves data in the requested unit system natively — we don't
        # convert on our side. Fahrenheit is requested so the raw numbers are
        # correct; we do our own F→C math for the dual display.
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        # Passing the IANA timezone (e.g. "America/Chicago") tells Open-Meteo to
        # align the hourly timestamps and daily summaries to local midnight — not
        # UTC midnight. Without this, "today's high" might reflect a different
        # calendar day depending on the time of day the script runs.
        "timezone": timezone,
        "forecast_days": 1,
    }

    # timeout=10 prevents the script from hanging indefinitely if the API is slow.
    # main.py wraps this in safe_fetch(), which catches the resulting exception,
    # so we let it propagate here rather than silently swallowing it.
    resp = requests.get(url, params=params, timeout=10)
    # raise_for_status() converts any 4xx/5xx HTTP response into a Python
    # exception (requests.HTTPError). Without this, a 500 response would return
    # silently with an empty or error body, producing confusing downstream failures.
    resp.raise_for_status()
    data = resp.json()

    current = data["current"]
    daily = data["daily"]
    hourly = data["hourly"]

    # Compute rounded Fahrenheit values once, then derive Celsius from them.
    # Rounding before the F→C conversion means both scales are independently
    # rounded to the nearest degree — which is what a user expects to see.
    temp_f = round(current["temperature_2m"])
    feels_f = round(current["apparent_temperature"])
    high_f = round(daily["temperature_2m_max"][0])  # [0] = first (only) day in the window
    low_f = round(daily["temperature_2m_min"][0])

    # The returned dict has a flat, explicit shape — all keys are strings, all
    # values are primitives. This makes the Jinja2 template straightforward:
    # {{ w.temp_f }}, {{ w.temp_c }}, etc. No nested access needed in the template.
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
    # Iterates the LOCATIONS list and calls fetch_weather() for each. This is a
    # list comprehension — equivalent to a for loop that appends to a list, but
    # expressed in one line. The result is a list of dicts, one per city, in the
    # same order as LOCATIONS.
    # Note: errors are NOT caught here — they propagate up to main.py's safe_fetch(),
    # which wraps the entire fetch_all_weather() call. If one city fails, the whole
    # weather section fails. An alternative would be per-city try/except here, but
    # a partial weather section (one city missing) would be more confusing in the
    # digest than skipping weather entirely.
    return [fetch_weather(loc["lat"], loc["lon"], loc["name"], loc["timezone"]) for loc in LOCATIONS]


if __name__ == "__main__":
    # This block only runs when the file is executed directly (python3 sources/weather.py),
    # not when it's imported by main.py. The __name__ == "__main__" check is Python's
    # standard way of writing "run this only as a script, not as a module."
    for w in fetch_all_weather():
        print(f"\nWeather for {w['location']} — {w['date']}")
        print(f"  Condition : {w['condition']}")
        print(f"  Current   : {w['temp_f']}°F / {w['temp_c']}°C  (feels like {w['feels_like_f']}°F / {w['feels_like_c']}°C)")
        print(f"  High / Low: {w['high_f']}°F / {w['high_c']}°C  —  {w['low_f']}°F / {w['low_c']}°C")
        print(f"  Wind      : {w['wind_mph']} mph")
        print(f"  Precip    : {w['precip_in']} in")
        print(f"  Rain      : {w['rain_summary']}")
