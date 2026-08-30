"""
Wildcat Brief — main entry point.

Fetches all sources with per-source fault isolation, renders the digest,
and sends it. A failure in any one source never kills the whole run.
"""

from formatter import render_digest
from delivery import send_digest
from sources.weather import fetch_all_weather
from sources.news import fetch_news
from sources.google_calendar import fetch_calendar_events


def safe_fetch(label: str, fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception as exc:
        print(f"[{label}] fetch failed: {exc}")
        return None


def main():
    print("Fetching sources...")

    weather_list = safe_fetch("weather", fetch_all_weather) or []
    news = safe_fetch("news", fetch_news) or []
    calendar_events = safe_fetch("calendar", fetch_calendar_events) or []

    print(f"  weather      : {len(weather_list)} location(s)")
    print(f"  news         : {len(news)} article(s)")
    print(f"  calendar     : {len(calendar_events)} event(s)")

    html = render_digest(weather_list=weather_list, calendar_events=calendar_events, news=news)
    send_digest(html)
    print("Done.")


if __name__ == "__main__":
    main()
