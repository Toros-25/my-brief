"""
One-time local OAuth2 flow for Google Calendar.

Run this script once interactively — it opens a browser, you approve access,
and it prints the refresh token. Paste that token into .env as GOOGLE_REFRESH_TOKEN.
After that, this script never needs to run again; the refresh token lets the
calendar module mint new access tokens automatically, indefinitely.

Usage:
    python3 auth/google_oauth.py
"""

import json
import os
from pathlib import Path

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = Path(__file__).parent.parent / "credentials.json"


def main():
    if not CREDENTIALS_FILE.exists():
        raise FileNotFoundError(
            f"credentials.json not found at {CREDENTIALS_FILE}\n"
            "Download it from Google Cloud Console → APIs & Services → Credentials."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(CREDENTIALS_FILE), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    print("\n--- OAuth complete ---")
    print(f"Access token  : {creds.token[:20]}...  (short-lived, ignore this)")
    print(f"Refresh token : {creds.refresh_token}")
    print("\nAdd this line to your .env file:")
    print(f"GOOGLE_REFRESH_TOKEN={creds.refresh_token}")


if __name__ == "__main__":
    main()
