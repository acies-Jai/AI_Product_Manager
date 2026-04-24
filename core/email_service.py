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


def send_or_log(to: list[str], subject: str, body: str, html_body: str | None = None,
                sender_name: str = "the PM team") -> str:
    """Send via Gmail SMTP if credentials are set, otherwise log to outputs/email_log.txt."""
    OUTPUTS_DIR.mkdir(exist_ok=True)
    sender = os.getenv("GMAIL_SENDER", "")
    password = os.getenv("GMAIL_APP_PASSWORD", "")

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

        final_html = html_body or _build_agent_email_html(plain_body, sender_name)
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
    """Fetch recent emails from Gmail inbox matching an IMAP search string."""
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


# ── HTML rendering helpers ────────────────────────────────────────────────────

_SECTION_COLORS = {
    "roadmap":         ("#5E17EB", "🗺️"),
    "key_focus_areas": ("#0EA5E9", "🎯"),
    "requirements":    ("#10B981", "📋"),
    "success_metrics": ("#F59E0B", "📊"),
    "impact_quadrant": ("#EF4444", "🔲"),
    "rice_score":      ("#8B5CF6", "⚖️"),
}

_ARTIFACT_LABELS = {
    "roadmap":         "Roadmap",
    "key_focus_areas": "Key Focus Areas",
    "requirements":    "Requirements",
    "success_metrics": "Success Metrics",
    "impact_quadrant": "Impact Quadrant",
    "rice_score":      "RICE Score",
}


def _md_table_to_html(md: str) -> str:
    rows = [r.strip() for r in md.strip().splitlines() if r.strip().startswith("|")]
    if not rows:
        return md
    html = ['<table style="width:100%;border-collapse:collapse;font-size:13px;margin:8px 0 12px;">']
    for i, row in enumerate(rows):
        cells = [c.strip() for c in row.strip("| ").split("|")]
        if all(set(c) <= set("-: ") for c in cells):
            continue
        tag = "th" if i == 0 else "td"
        style = (
            'style="background:#1A0533;color:rgba(255,255,255,0.8);padding:9px 12px;'
            'text-align:left;font-size:11px;letter-spacing:0.5px;text-transform:uppercase;"'
            if i == 0
            else f'style="padding:8px 12px;border-bottom:1px solid #f0edf8;'
                 f'background:{"#fff" if i % 2 else "#faf8ff"};"'
        )
        html.append("<tr>" + "".join(f"<{tag} {style}>{c}</{tag}>" for c in cells) + "</tr>")
    html.append("</table>")
    return "\n".join(html)


def _md_to_html(md: str) -> str:
    """Convert artifact markdown (tables, bullets, bold, headings) to inline-styled HTML."""
    md = re.sub(
        r"(\|.+\|\n)(\|[-| :]+\|\n)((?:\|.+\|\n?)*)",
        lambda m: _md_table_to_html(m.group(0)),
        md,
    )
    lines = md.splitlines()
    out: list[str] = []
    in_ul = False

    for line in lines:
        if line.startswith("<t"):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            out.append(line)
            continue

        stripped = line.strip()

        if stripped.startswith("- ") or stripped.startswith("* "):
            if not in_ul:
                out.append('<ul style="margin:4px 0 10px 18px;padding:0;">')
                in_ul = True
            item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped[2:])
            out.append(f'<li style="margin:4px 0;color:#374151;">{item}</li>')
            continue

        if in_ul:
            out.append("</ul>")
            in_ul = False

        m = re.match(r"^(#{2,4})\s+(.+)", stripped)
        if m:
            level = min(len(m.group(1)) + 1, 5)
            text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", m.group(2))
            out.append(
                f'<h{level} style="margin:16px 0 6px;color:#1A0533;'
                f'font-size:{18 - level}px;font-weight:700;">{text}</h{level}>'
            )
            continue

        m = re.match(r"^\d+\.\s+\*\*(.+?)\*\*(.*)$", stripped)
        if m:
            out.append(
                f'<p style="margin:10px 0 3px;">'
                f'<strong style="color:#5E17EB;">{m.group(1)}</strong>'
                f'<span style="color:#374151;">{m.group(2)}</span></p>'
            )
            continue

        if not stripped:
            out.append('<div style="height:8px;"></div>')
            continue

        text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", stripped)
        out.append(f'<p style="margin:4px 0;line-height:1.65;color:#374151;">{text}</p>')

    if in_ul:
        out.append("</ul>")

    return "\n".join(out)


def _build_agent_email_html(body: str, sender_name: str = "the PM team") -> str:
    """Wrap an agent-composed plain/markdown body in a fully branded HTML email."""
    body_html = _md_to_html(body)
    today = date.today().strftime("%d %b %Y")
    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0edf8;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0edf8;padding:32px 16px;">
    <tr><td align="center">
      <table width="620" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:14px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(94,23,235,0.12);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#5E17EB 0%,#7C3AED 60%,#9F67FA 100%);
                     padding:28px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="color:#fff;font-size:24px;font-weight:800;
                              letter-spacing:-0.5px;line-height:1;">⚡ Zepto</div>
                  <div style="color:rgba(255,255,255,0.6);font-size:10px;letter-spacing:2.5px;
                              text-transform:uppercase;margin-top:5px;font-weight:600;">
                    PM Intelligence Layer
                  </div>
                </td>
                <td align="right" valign="middle">
                  <div style="background:rgba(255,255,255,0.15);border-radius:20px;
                              padding:5px 14px;color:#fff;font-size:11px;font-weight:600;">
                    {today}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Gradient accent line -->
        <tr>
          <td style="height:3px;background:linear-gradient(90deg,#5E17EB,#9F67FA,#EDE9FF);"></td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:28px 32px 12px;">
            <div style="font-size:14px;color:#1A0533;line-height:1.75;">
              {body_html}
            </div>
          </td>
        </tr>

        <!-- Signature -->
        <tr>
          <td style="padding:8px 32px 28px;">
            <table cellpadding="0" cellspacing="0"
                   style="border-left:3px solid #5E17EB;padding-left:14px;">
              <tr>
                <td>
                  <div style="font-size:12px;font-weight:700;color:#5E17EB;line-height:1.4;">
                    Zepto PM Intelligence Layer
                  </div>
                  <div style="font-size:11px;color:#9CA3AF;margin-top:2px;">
                    Sent on behalf of {sender_name}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="padding:14px 32px 20px;background:#faf8ff;border-top:1px solid #EDE9FF;">
            <p style="margin:0;font-size:11px;color:#9CA3AF;line-height:1.6;">
              Generated by <strong style="color:#5E17EB;">Zepto PM Intelligence Layer</strong>.
              Open the PM Assistant app for full interactive artefacts.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _artifact_email_html(artifacts: dict[str, str]) -> str:
    """Build a branded HTML email with all artefact sections rendered as styled cards."""
    sections_html: list[str] = []

    for key, label in _ARTIFACT_LABELS.items():
        content = artifacts.get(key, "").strip()
        if not content:
            continue
        color, icon = _SECTION_COLORS.get(key, ("#5E17EB", "📄"))
        if len(content) > 1400:
            content = content[:1400] + "\n\n*(truncated — full version in the PM Assistant app)*"
        body_html = _md_to_html(content)
        sections_html.append(f"""
        <tr>
          <td style="padding:0 32px 24px;">
            <table width="100%" cellpadding="0" cellspacing="0"
                   style="border:1px solid #EDE9FF;border-radius:10px;overflow:hidden;">
              <tr>
                <td style="background:{color};padding:10px 16px;">
                  <span style="color:#fff;font-weight:700;font-size:12px;letter-spacing:1px;
                               text-transform:uppercase;">
                    {icon}&nbsp; {label}
                  </span>
                </td>
              </tr>
              <tr>
                <td style="padding:16px 18px;font-size:13px;color:#374151;
                           line-height:1.65;background:#fff;">
                  {body_html}
                </td>
              </tr>
            </table>
          </td>
        </tr>""")

    all_sections = "\n".join(sections_html)
    today = date.today().strftime("%d %b %Y")

    return f"""\
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0edf8;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0edf8;padding:32px 16px;">
    <tr><td align="center">
      <table width="660" cellpadding="0" cellspacing="0"
             style="background:#fff;border-radius:14px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(94,23,235,0.12);">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#5E17EB 0%,#7C3AED 60%,#9F67FA 100%);
                     padding:28px 32px;">
            <table width="100%" cellpadding="0" cellspacing="0">
              <tr>
                <td>
                  <div style="color:#fff;font-size:26px;font-weight:800;
                              letter-spacing:-0.5px;">⚡ Zepto</div>
                  <div style="color:rgba(255,255,255,0.6);font-size:10px;letter-spacing:2.5px;
                              text-transform:uppercase;margin-top:5px;font-weight:600;">
                    PM Intelligence Layer
                  </div>
                </td>
                <td align="right" valign="middle">
                  <div style="background:rgba(255,255,255,0.15);border-radius:20px;
                              padding:6px 14px;color:#fff;font-size:11px;font-weight:600;">
                    {today}
                  </div>
                </td>
              </tr>
            </table>
          </td>
        </tr>

        <!-- Gradient accent -->
        <tr>
          <td style="height:3px;background:linear-gradient(90deg,#5E17EB,#9F67FA,#EDE9FF);"></td>
        </tr>

        <!-- Intro -->
        <tr>
          <td style="padding:24px 32px 16px;">
            <p style="margin:0;font-size:15px;font-weight:600;color:#1A0533;">Hi team,</p>
            <p style="margin:10px 0 0;font-size:14px;color:#555;line-height:1.7;">
              Your updated PM artefacts for the
              <strong style="color:#1A0533;">Customer App &amp; Checkout Experience</strong>
              charter are ready. Review each section below and share your inputs with
              <strong style="color:#5E17EB;">Jaiadithya</strong> (Director of Product).
            </p>
          </td>
        </tr>

        <!-- Artefact sections -->
        {all_sections}

        <!-- Footer -->
        <tr>
          <td style="padding:18px 32px 24px;background:#faf8ff;border-top:1px solid #EDE9FF;">
            <p style="margin:0;font-size:11px;color:#9CA3AF;line-height:1.6;">
              Generated automatically by
              <strong style="color:#5E17EB;">Zepto PM Intelligence Layer</strong>.
              This email is a summary — open the PM Assistant app for full interactive artefacts.
            </p>
          </td>
        </tr>

      </table>
    </td></tr>
  </table>
</body>
</html>"""


def notify_with_recipients(artifacts: dict[str, str], recipients: list[str]) -> str:
    """Send artifact notification email to a specific list of recipients."""
    config = _load_config()
    subject = (
        config.get("triggers", {})
        .get("artifacts_generated", {})
        .get("subject", "PM Artifacts Updated")
        .replace("{date}", str(date.today()))
    )
    plain_body = (
        "Hi,\n\nYour updated PM artefacts for the Customer App & Checkout Experience "
        "charter are ready. Please open the PM Assistant app to review them.\n\n"
        "— Zepto PM Intelligence Layer"
    )
    return send_or_log(recipients, subject, plain_body, html_body=_artifact_email_html(artifacts))


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
