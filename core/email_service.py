import os
import smtplib
from datetime import date
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import yaml

from core.client import OUTPUTS_DIR, ROOT

EMAIL_CONFIG = ROOT / "config" / "email_config.yaml"


def _load_config() -> dict:
    if EMAIL_CONFIG.exists():
        with open(EMAIL_CONFIG, encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def send_or_log(to: list[str], subject: str, body: str) -> str:
    """Send via Gmail SMTP if credentials are set, otherwise log to outputs/email_log.txt."""
    OUTPUTS_DIR.mkdir(exist_ok=True)
    sender = os.getenv("GMAIL_SENDER", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")

    mode = "SENT" if (sender and password) else "SIMULATED"
    with open(OUTPUTS_DIR / "email_log.txt", "a", encoding="utf-8") as f:
        f.write(
            f"\n{'─' * 60}\n[{mode}] {date.today()}\n"
            f"TO: {', '.join(to)}\nSUBJECT: {subject}\n{body}\n"
        )

    if not (sender and password):
        return f"simulated (logged) — Gmail not configured. Recipients: {', '.join(to)}"

    try:
        msg = MIMEMultipart()
        msg["From"] = sender
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
            srv.login(sender, password)
            srv.sendmail(sender, to, msg.as_string())
        return f"sent to {', '.join(to)}"
    except Exception as e:
        return f"failed ({e}) — logged to email_log.txt"


def notify_artifacts_generated(artifacts: dict[str, str]) -> str:
    config = _load_config()
    trigger = config.get("triggers", {}).get("artifacts_generated", {})
    recipients: list[str] = trigger.get("recipients", [])
    if not recipients:
        return "no recipients configured"
    subject = trigger.get("subject", "PM Artifacts Updated").replace("{date}", str(date.today()))
    body = trigger.get("body", "PM artifacts have been updated.")
    return send_or_log(recipients, subject, body)
