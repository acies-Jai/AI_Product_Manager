import imaplib
import os
import re
import smtplib
from datetime import date
from email import message_from_bytes
from email.header import decode_header
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


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", text).strip()


def read_inbox(query: str = "ALL", max_results: int = 5) -> list[dict]:
    """
    Fetch recent emails from Gmail inbox matching an IMAP search string.
    Requires GMAIL_SENDER and GMAIL_APP_PASSWORD in .env, and IMAP enabled in Gmail settings.
    """
    sender = os.getenv("GMAIL_SENDER", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")
    if not (sender and password):
        return [{"error": "GMAIL_SENDER / GMAIL_APP_PASSWORD not set — inbox reading unavailable"}]

    with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
        mail.login(sender, password)
        mail.select("inbox")
        _, uids = mail.search(None, query)
        uid_list = uids[0].split()
        if not uid_list:
            return []
        uid_list = uid_list[-max_results:]

        results = []
        for uid in reversed(uid_list):
            _, data = mail.fetch(uid, "(RFC822)")
            msg = message_from_bytes(data[0][1])
            raw_subject, enc = decode_header(msg["Subject"] or "")[0]
            if isinstance(raw_subject, bytes):
                subject = raw_subject.decode(enc or "utf-8", errors="replace")
            else:
                subject = raw_subject or ""
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    ct = part.get_content_type()
                    if ct == "text/plain":
                        body = part.get_payload(decode=True).decode(errors="replace")
                        break
                    if ct == "text/html" and not body:
                        body = _strip_html(part.get_payload(decode=True).decode(errors="replace"))
            else:
                raw = msg.get_payload(decode=True).decode(errors="replace")
                body = _strip_html(raw) if msg.get_content_type() == "text/html" else raw
            results.append({
                "sender": msg.get("From", ""),
                "subject": subject,
                "date": msg.get("Date", ""),
                "body_snippet": body[:500].strip(),
            })
    return results


def _artifact_email_body(artifacts: dict[str, str]) -> str:
    """Build a plain-text email body that includes a summary of each artifact."""
    LABELS = {
        "roadmap": "ROADMAP",
        "key_focus_areas": "KEY FOCUS AREAS",
        "requirements": "REQUIREMENTS",
        "success_metrics": "SUCCESS METRICS",
        "impact_quadrant": "IMPACT QUADRANT",
    }
    sections: list[str] = [
        "Hi team,\n\n"
        "The PM Assistant has generated an updated set of artefacts for the\n"
        "Customer App & Checkout Experience charter. Full details below.\n"
    ]
    for key, label in LABELS.items():
        content = artifacts.get(key, "").strip()
        if not content:
            continue
        # Truncate very long sections to keep the email readable
        preview = content if len(content) <= 1200 else content[:1200] + "\n… (truncated — full version in the app)"
        sections.append(f"\n{'─' * 50}\n{label}\n{'─' * 50}\n{preview}")

    sections.append(
        "\n\nPlease review and share your inputs with Jaiadithya (Director of Product).\n\n"
        "— PM Intelligence Layer"
    )
    return "\n".join(sections)


def notify_artifacts_generated(artifacts: dict[str, str]) -> str:
    config = _load_config()
    trigger = config.get("triggers", {}).get("artifacts_generated", {})
    recipients: list[str] = trigger.get("recipients", [])
    if not recipients:
        return "no recipients configured"
    subject = trigger.get("subject", "PM Artifacts Updated").replace("{date}", str(date.today()))
    body = _artifact_email_body(artifacts)
    return send_or_log(recipients, subject, body)
