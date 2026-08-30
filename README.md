# Your Morning Brief

A daily digest bot that emails a personalized morning summary every day at 8:30 AM. Pulls live data from four sources, formats it into an HTML email, and delivers it automatically via GitHub Actions — no server required.

## What it includes

- **Weather** — current conditions, high/low, wind, and a plain-English rain forecast for two cities (Evanston, IL and Toronto, ON), in both °F and °C. Powered by [Open-Meteo](https://open-meteo.com/) (free, no API key).
- **Immigration & visa news** — top 10 most recent articles about F-1 visas, H-1B visas, OPT/CPT, SEVIS, and international student policy. Aggregated from NPR, BBC, The Guardian, Inside Higher Ed, Immigration Impact, and targeted Google News search feeds. Keyword-filtered so only relevant articles get through.
- **Google Calendar** — today's events pulled from your primary calendar via OAuth2.

## Tech stack

- Python 3.12
- `requests`, `feedparser`, `Jinja2`, `python-dotenv`
- `google-api-python-client`, `google-auth-oauthlib` — Calendar OAuth2
- GitHub Actions — scheduled delivery

## Project structure

```
├── sources/
│   ├── weather.py          # Open-Meteo weather fetcher
│   ├── news.py             # RSS + Google News aggregator with keyword filter
│   └── google_calendar.py  # Google Calendar API client
├── auth/
│   └── google_oauth.py     # One-time local script to generate OAuth refresh token
├── templates/
│   └── digest.html.j2      # Jinja2 HTML email template
├── formatter.py            # Renders template with aggregated source data
├── delivery.py             # Gmail SMTP delivery
├── main.py                 # Orchestrator with per-source fault isolation
└── .github/workflows/
    └── daily-brief.yml     # Scheduled GitHub Actions workflow
```

## How it works

`main.py` calls each source inside a `safe_fetch()` wrapper — if one source fails, the rest still run and the digest still sends. The aggregated data is rendered into an HTML email via Jinja2 and delivered over Gmail SMTP.

The GitHub Actions workflow runs on a cron schedule (`30 13 * * *` UTC = 8:30 AM EST). All credentials are stored as encrypted repository secrets — nothing sensitive lives in the code.

## Setup

### 1. Clone and install dependencies

```bash
git clone https://github.com/Toros-25/my-brief.git
cd my-brief
pip install -r requirements.txt
```

### 2. Google Calendar OAuth (one-time)

1. Create a project at [console.cloud.google.com](https://console.cloud.google.com)
2. Enable the **Google Calendar API**
3. Configure an OAuth consent screen (External, testing mode)
4. Create an **OAuth 2.0 Client ID** (Desktop app type) and download `credentials.json` to the project root
5. Add yourself as a test user under the OAuth consent screen → Audience
6. Run the auth script:
   ```bash
   python3 auth/google_oauth.py
   ```
   A browser tab opens — log in and approve. The script prints your `GOOGLE_REFRESH_TOKEN`.

### 3. Gmail App Password

In your Google Account → Security → 2-Step Verification → App passwords, generate a password for this app. This is required because Google blocks direct password authentication for SMTP.

### 4. Environment variables

Create a `.env` file at the project root (never committed):

```
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
GOOGLE_REFRESH_TOKEN=your_refresh_token
GMAIL_USER=your@gmail.com
GMAIL_APP_PASSWORD=your_app_password
TO_EMAIL=your@gmail.com
```

### 5. Run locally

```bash
python3 main.py
```

### 6. Deploy to GitHub Actions

Add the same six values as encrypted secrets at:
`github.com/your-username/your-repo/settings/secrets/actions`

The workflow runs automatically on schedule. You can also trigger it manually from the Actions tab.

## Fault tolerance

Each source is fetched inside `safe_fetch()` in `main.py`. A failure in any one source (network timeout, API error, bad credentials) prints a warning and returns `None` — the digest still renders and sends with the remaining sources. The Jinja2 template handles missing sections gracefully with fallback messages.
