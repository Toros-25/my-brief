"""
Renders the digest HTML from source data using the Jinja2 template.
"""

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from jinja2 import Environment, FileSystemLoader

TEMPLATE_DIR = Path(__file__).parent / "templates"
TEMPLATE_NAME = "digest.html.j2"
LOCAL_TZ = ZoneInfo("America/Chicago")


def render_digest(
    weather_list: list[dict],
    calendar_events: list[dict],
    news: list[dict],
) -> str:
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)), autoescape=True)
    template = env.get_template(TEMPLATE_NAME)

    now = datetime.now(LOCAL_TZ)
    return template.render(
        date=now.strftime("%A, %B %d"),
        generated_at=now.strftime("%-I:%M %p"),
        weather_list=weather_list,
        calendar_events=calendar_events,
        news=news,
    )
