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


_SIGNATURE = "\n\nBest regards,\nZepto PM Intelligence Layer"

_AGENT_EMAIL_TEMPLATE = """\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#f5f5f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f5;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:8px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">
        <tr>
          <td style="background:#5E17EB;padding:24px 32px;">
            <span style="color:#ffffff;font-size:22px;font-weight:700;">⚡ Zepto</span>
            <span style="color:rgba(255,255,255,0.7);font-size:13px;margin-left:8px;">PM Intelligence Layer</span>
          </td>
        </tr>
        <tr>
          <td style="padding:28px 32px;color:#333;font-size:15px;line-height:1.7;">
            {body_html}
          </td>
        </tr>
        <tr>
          <td style="padding:16px 32px 24px;background:#fafafa;border-top:1px solid #f0f0f0;font-size:12px;color:#999;">
            This message was sent by the Zepto PM Intelligence Layer on behalf of {sender_name}.
          </td>
        </tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def send_or_log(to: list[str], subject: str, body: str, html_body: str | None = None,
                sender_name: str = "the PM team") -> str:
    """Send via Gmail SMTP if credentials are set, otherwise log to outputs/email_log.txt.

    If html_body is provided it is sent as the HTML alternative; body is used as plain-text
    fallback and for logging. For agent-sent emails (no html_body) a signature is appended
    and the body is wrapped in a minimal branded HTML template.
    """
    OUTPUTS_DIR.mkdir(exist_ok=True)
    sender = os.getenv("GMAIL_SENDER", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")

    # Append signature to plain body for agent-sent emails
    plain_body = body if html_body else body + _SIGNATURE

    mode = "SENT" if (sender and password) else "SIMULATED"
    with open(OUTPUTS_DIR / "email_log.txt", "a", encoding="utf-8") as f:
        f.write(
            f"\n{'─' * 60}\n[{mode}] {date.today()}\n"
            f"TO: {', '.join(to)}\nSUBJECT: {subject}\n{plain_body}\n"
        )

    if not (sender and password):
        return f"simulated (logged) — Gmail not configured. Recipients: {', '.join(to)}"

    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = sender
        msg["To"] = ", ".join(to)
        msg["Subject"] = subject
        msg.attach(MIMEText(plain_body, "plain", "utf-8"))

        # Use provided HTML or wrap plain body in branded template
        final_html = html_body or _AGENT_EMAIL_TEMPLATE.format(
            body_html=plain_body.replace("\n", "<br>"),
            sender_name=sender_name,
        )
        msg.attach(MIMEText(final_html, "html", "utf-8"))

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


_SECTION_COLORS = {
    "roadmap":        ("#5E17EB", "🗺️"),
    "key_focus_areas": ("#0EA5E9", "🎯"),
    "requirements":   ("#10B981", "📋"),
    "success_metrics": ("#F59E0B", "📊"),
    "impact_quadrant": ("#EF4444", "🔲"),
    "rice_score":     ("#8B5CF6", "⚖️"),
}

_ARTIFACT_LABELS = {
    "roadmap":        "Roadmap",
    "key_focus_areas": "Key Focus Areas",
    "requirements":   "Requirements",
    "success_metrics": "Success Metrics",
    "impact_quadrant": "Impact Quadrant",
    "rice_score":     "RICE Score",
}


def _md_table_to_html(md: str) -> str:
    """Convert a markdown table block to an HTML table."""
    rows = [r.strip() for r in md.strip().splitlines() if r.strip().startswith("|")]
    if not rows:
        return md
    html = ['<table style="width:100%;border-collapse:collapse;font-size:13px;margin:8px 0;">']
    for i, row in enumerate(rows):
        cells = [c.strip() for c in row.strip("| ").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue  # skip separator row
        tag = "th" if i == 0 else "td"
        style = (
            'style="background:#5E17EB;color:#fff;padding:8px 10px;text-align:left;"'
            if i == 0
            else 'style="padding:7px 10px;border-bottom:1px solid #f0f0f0;"'
        )
        html.append("<tr>" + "".join(f"<{tag} {style}>{c}</{tag}>" for c in cells) + "</tr>")
    html.append("</table>")
    return "\n".join(html)


def _md_to_html(md: str) -> str:
    """Convert artifact markdown (tables, bullets, bold, headings) to inline-styled HTML."""
    # Convert markdown tables first
    md = re.sub(
        r"(\|.+\|\n)(\|[-| :]+\|\n)((?:\|.+\|\n?)*)",
        lambda m: _md_table_to_html(m.group(0)),
        md,
    )
    lines = md.splitlines()
    out: list[str] = []
    in_ul = False

    for line in lines:
        # Already converted table rows — pass through
        if line.startswith("<t"):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(line)
            continue

        stripped = line.strip()

        # Bullet list
        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_ul:
                out.append('<ul style="margin:4px 0 8px 16px;padding:0;">')
                in_ul = True
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped[2:])
            out.append(f'<li style="margin:3px 0;">{item}</li>')
            continue

        if in_ul:
            out.append("</ul>")
            in_ul = False

        # Headings
        m = re.match(r"^(#{2,4})\s+(.+)", stripped)
        if m:
            level = min(len(m.group(1)) + 1, 5)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", m.group(2))
            out.append(
                f'<h{level} style="margin:14px 0 4px;color:#333;font-size:{18 - level}px;">{text}</h{level}>'
            )
            continue

        # Numbered items
        m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*(.*)$", stripped)
        if m:
            out.append(
                f'<p style="margin:8px 0 2px;"><strong style="color:#111;">{m.group(1)}</strong>'
                f'{m.group(2)}</p>'
            )
            continue

        # Empty line
        if not stripped:
            out.append('<div style="height:6px;"></div>')
            continue

        # Normal paragraph — apply inline bold
        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
        out.append(f'<p style="margin:4px 0;line-height:1.6;">{text}</p>')

    if in_ul:
        out.append("</ul>")

    return "\n".join(out)


def _artifact_email_html(artifacts: dict[str, str]) -> str:
    """Build a branded HTML email with all artefact sections rendered as styled cards."""
    sections_html: list[str] = []

    for key, label in _ARTIFACT_LABELS.items():
        content = artifacts.get(key, "").strip()
        if not content:
            continue
        color, icon = _SECTION_COLORS.get(key, ("#5E17EB", "📄"))
        # Truncate very long sections in email
        if len(content) > 1400:
            content = content[:1400] + "\n\n*(truncated — full version in the PM Assistant app)*"
        body_html = _md_to_html(content)
        sections_html.append(f"""
        <tr>
          <td style="padding:0 32px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #e8e8e8;border-radius:8px;overflow:hidden;">
              <tr>
                <td style="background:{color};padding:10px 16px;">
                  <span style="color:#fff;font-weight:700;font-size:13px;letter-spacing:0.5px;">
                    {icon}&nbsp; {label.upper()}
                  </span>
                </td>
              </tr>
              <tr>
                <td style="padding:16px;font-size:13px;color:#333;line-height:1.6;background:#fff;">
                  {body_html}
                </td>
              </tr>
            </table>
          </td>
        </tr>""")

    all_sections = "\n".join(sections_html)

    return f"""\
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f0edf8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f0edf8;padding:32px 16px;">
    <tr><td align="center">
      <table width="660" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 4px 16px rgba(94,23,235,0.12);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#5E17EB 0%,#7C3AED 100%);padding:28px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="color:#fff;font-size:26px;font-weight:800;letter-spacing:-0.5px;">⚡ Zepto</div>
                  <div style="color:rgba(255,255,255,0.75);font-size:13px;margin-top:2px;">PM Intelligence Layer</div>
                </td>
                <td align="right" valign="middle">
                  <div style="background:rgba(255,255,255,0.15);border-radius:20px;padding:6px 14px;
                              color:#fff;font-size:12px;font-weight:600;">
                    {date.today().strftime("%d %b %Y")}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:24px 32px 16px;">
            <p style="margin:0;font-size:15px;color:#333;line-height:1.6;">Hi team,</p>
            <p style="margin:10px 0 0;font-size:14px;color:#555;line-height:1.7;">
              Your updated PM artefacts for the <strong>Customer App &amp; Checkout Experience</strong>
              charter are ready. Review each section below and share your inputs with
              <strong>Jaiadithya</strong> (Director of Product).
            </p>
          </td>
        </tr>

        <!-- Artifact sections -->
        {all_sections}

        <!-- Footer -->
        <tr>
          <td style="padding:20px 32px 28px;background:#fafafa;border-top:1px solid #f0f0f0;">
            <p style="margin:0;font-size:12px;color:#999;line-height:1.6;">
              Generated automatically by <strong style="color:#5E17EB;">Zepto PM Intelligence Layer</strong>.
              This email contains a summary — open the PM Assistant app for full interactive artefacts.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def notify_artifacts_generated(artifacts: dict[str, str]) -> str:
    config = _load_config()
    trigger = config.get("triggers", {}).get("artifacts_generated", {})
    recipients: list[str] = trigger.get("recipients", [])
    if not recipients:
        return "no recipients configured"
    subject = trigger.get("subject", "PM Artifacts Updated").replace("{date}", str(date.today()))
    plain_body = (
        "Hi team,\n\nYour updated PM artefacts for the Customer App & Checkout Experience "
        "charter are ready. Please open the PM Assistant app to review them.\n\n"
        "— Zepto PM Intelligence Layer"
    )
    html_body = _artifact_email_html(artifacts)
    return send_or_log(recipients, subject, plain_body, html_body=html_body)
