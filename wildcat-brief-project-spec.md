# Project: Wildcat Brief

**One-line pitch:** A daily automated digest pulling together your Canvas assignments, Google Calendar events, local weather, and top headlines — delivered to your inbox every morning through a scheduled pipeline.

**Build philosophy:** One module at a time. Each source is written and tested standalone (run it, print the output, confirm it works) *before* it's wired into the aggregator. Nothing gets combined until each piece is proven independently — this avoids debugging four APIs at once when something breaks.

---

## Sources — all confirmed free

| Source | Method | Free tier |
|---|---|---|
| Weather | Open-Meteo | No key, no signup, free for non-commercial use up to 10,000 calls/day |
| News | RSS feeds via `feedparser` | Fully free, no key, no usage terms to violate (NewsAPI.org's free tier is dev/localhost-only and will silently break once it's running from a GitHub Actions server, so it's deliberately excluded) |
| Canvas | Canvas REST API, personal access token | Free — included with your existing Northwestern account |
| Google Calendar | Google Calendar API, OAuth2 | Free — Google's default quota (1,000,000 requests/day) is far beyond personal use |

No market data in this version — cut per your last message, so it's Canvas + Calendar + weather + news only.

## Tech stack

- Python 3.12
- `requests` — Canvas, Open-Meteo
- `feedparser` — news via RSS (XML parsing, a nice contrast to the JSON APIs)
- `google-api-python-client` + `google-auth-oauthlib` — Google Calendar OAuth2
- `Jinja2` — HTML digest templating
- GitHub Actions — scheduler + encrypted secrets

## Repo structure

```
wildcat-brief/
├── .github/workflows/daily-brief.yml   # added last, once everything works locally
├── sources/
│   ├── weather.py
│   ├── news.py
│   ├── canvas.py
│   └── google_calendar.py
├── auth/
│   └── google_oauth.py                 # one-time local auth + refresh logic
├── templates/
│   └── digest.html.j2
├── formatter.py
├── delivery.py
├── main.py
└── requirements.txt
```

---

## Build order — one module at a time

**M1 — Weather (`sources/weather.py`)**
No auth, no signup. Write the function, run it standalone, print the output. This is your "does my dev environment even work" checkpoint.

**M2 — News (`sources/news.py`)**
Pick 2–3 RSS feeds (e.g. NPR, Reuters, BBC each publish public feed URLs), parse with `feedparser`, return the top N headlines. Also standalone and no auth — good second checkpoint before touching anything that requires credentials.

**M3 — Canvas (`sources/canvas.py`)**
Generate a personal access token: Canvas → Account → Settings → "+ New Access Token". Hit `GET /api/v1/users/self/todo` for pending items, or `GET /api/v1/courses/:id/assignments` for a specific course's due dates. This is your first taste of key-based auth — one header, no OAuth complexity yet.

**M4 — Google Calendar (`sources/google_calendar.py` + `auth/google_oauth.py`)**
The hardest module, done last and in isolation. Steps:
1. Go to console.cloud.google.com, create a new project.
2. APIs & Services → Library → enable the **Google Calendar API**.
3. APIs & Services → OAuth consent screen → set up as "External" (or "Internal" if you use a Google Workspace account), fill in the minimal required fields.
4. Credentials → Create Credentials → OAuth client ID → Application type: **Desktop app**. Download the resulting `credentials.json`.
5. Locally, run a one-time script using `google-auth-oauthlib`'s `InstalledAppFlow` — it opens a browser, you log in and approve access, and it returns credentials including a **refresh token**.
6. Save that refresh token somewhere safe (not committed to git). This is what lets the script mint new access tokens automatically, forever, with no browser step — which is exactly what you need for it to run unattended in GitHub Actions.
7. Write `sources/google_calendar.py` to use the refresh token to authenticate and call `calendarapi.events().list()` for today's events.

Test this module completely on its own before touching `main.py`. Getting a green result here — a real list of today's events printed to your terminal — is the single biggest milestone in the whole project.

**M5 — Aggregator, formatter, delivery**
Only now do the four modules get combined. `main.py` calls each with a `try/except` per source (`safe_fetch`, same pattern as before) so one failing source never kills the whole digest. `formatter.py` renders a Jinja2 HTML template; `delivery.py` sends it via Gmail SMTP.

**M6 — Automate**
Once `python main.py` works end-to-end locally, move credentials into GitHub Actions secrets (including the Calendar refresh token) and add the scheduled workflow. This is the last step, not the first — automating something that doesn't work yet just multiplies the places something can break.

## Secrets you'll need in GitHub Actions

```
CANVAS_TOKEN
CANVAS_BASE_URL
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REFRESH_TOKEN
GMAIL_USER
GMAIL_APP_PASSWORD
TO_EMAIL
```

## Why this is resume-worthy

- Real OAuth2 flow with refresh-token handling for unattended/server-side auth — the part most student projects skip
- Two different auth patterns in one project (Canvas's simple token vs. Google's full OAuth2)
- Two different data formats (JSON from Canvas/Calendar/weather, XML/RSS from news)
- Fault-tolerant pipeline design — partial failure never breaks the whole run
- Scheduled, production-style automation via CI/CD
