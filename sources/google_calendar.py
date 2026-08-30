"""
M4 — Google Calendar via Calendar API + OAuth2 refresh token.

Reads GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN from .env.
No browser interaction after the one-time auth/google_oauth.py run — the refresh
token mints new access tokens automatically.

Returns today's events sorted by start time; prints a summary when run standalone.
"""

import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
LOCAL_TZ = ZoneInfo("America/Chicago")


def _build_credentials() -> Credentials:
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def _fmt_time(dt_str: str, is_all_day: bool) -> str:
    if is_all_day:
        return "All day"
    dt = datetime.fromisoformat(dt_str).astimezone(LOCAL_TZ)
    return dt.strftime("%-I:%M %p")


def fetch_calendar_events(calendar_id: str = "primary") -> list[dict]:
    creds = _build_credentials()
    service = build("calendar", "v3", credentials=creds, cache_discovery=False)

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = start_of_day + timedelta(days=1)

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=start_of_day.isoformat(),
        timeMax=end_of_day.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for item in result.get("items", []):
        start = item["start"]
        is_all_day = "date" in start and "dateTime" not in start
        start_str = start.get("dateTime") or start.get("date")
        events.append({
            "title": item.get("summary", "(no title)"),
            "start": _fmt_time(start_str, is_all_day),
            "location": item.get("location", ""),
            "description": item.get("description", ""),
            "all_day": is_all_day,
        })
    return events


if __name__ == "__main__":
    today = datetime.now(LOCAL_TZ).strftime("%A, %B %d")
    print(f"Google Calendar — {today}\n")
    events = fetch_calendar_events()
    if not events:
        print("  No events today.")
    else:
        for e in events:
            loc = f"  @ {e['location']}" if e["location"] else ""
            print(f"  {e['start']:>10}  {e['title']}{loc}")
