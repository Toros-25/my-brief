"""
Sends the digest HTML via Gmail SMTP.

Reads GMAIL_USER, GMAIL_APP_PASSWORD, and TO_EMAIL from .env.
Uses port 587 + STARTTLS — no third-party library needed beyond stdlib.
"""

import os
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from zoneinfo import ZoneInfo

from dotenv import load_dotenv

load_dotenv()

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
LOCAL_TZ = ZoneInfo("America/Chicago")


def send_digest(html: str) -> None:
    gmail_user = os.environ["GMAIL_USER"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    to_email = os.environ["TO_EMAIL"]

    subject = f"Your Morning Brief — {datetime.now(LOCAL_TZ).strftime('%A, %B %d')}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_user
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.ehlo()
        server.starttls()
        server.login(gmail_user, app_password)
        server.sendmail(gmail_user, to_email, msg.as_string())

    print(f"[delivery] Sent to {to_email}")
