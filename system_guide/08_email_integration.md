# 08 — Email Integration (SMTP + IMAP)

## Basics — email protocols

Email operates on two entirely separate protocols for sending and receiving:

**SMTP (Simple Mail Transfer Protocol)** — sending mail
- Port 587: STARTTLS (plain connection upgraded to encrypted)
- Port 465: SSL/TLS from the start (used in this project)
- The client authenticates, hands off the message to the mail server, done.

**IMAP (Internet Message Access Protocol)** — reading mail
- Port 993: SSL/TLS
- Messages remain on the server; the client accesses them on demand
- Alternative: POP3 (port 995) downloads and deletes — IMAP is preferred for agents because
  you can search without removing messages.

Both protocols are decades old. All major email providers (Gmail, Outlook, Yahoo) support them.
Modern providers require **App Passwords** instead of your account password — a separate
16-character credential with limited scope, separate from your main account login.

---

## Going deeper

### Gmail App Passwords

Gmail requires 2-Step Verification to be enabled, then you generate an App Password:
1. Go to Google Account → Security → 2-Step Verification → App Passwords
2. Select "Mail" and the device
3. Google generates a 16-character password (e.g., `abcd efgh ijkl mnop`)
4. Use this in your `.env` as `GMAIL_APP_PASSWORD` (without spaces)

This password only works for SMTP/IMAP. It cannot be used to log into gmail.com. If compromised,
you revoke it without affecting your main account.

### SMTP send flow

```python
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

msg = MIMEMultipart()
msg["From"] = sender
msg["To"] = ", ".join(recipients)
msg["Subject"] = subject
msg.attach(MIMEText(body, "plain"))

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
    srv.login(sender, password)
    srv.sendmail(sender, recipients, msg.as_string())
```

`MIME` (Multipurpose Internet Mail Extensions) is the standard for encoding email messages.
`MIMEMultipart` creates a container that can hold multiple parts (e.g., plain text + HTML +
attachments). `MIMEText("plain")` adds a plain-text body part.

### IMAP search flow

```python
import imaplib

with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
    mail.login(sender, password)
    mail.select("inbox")
    _, uids = mail.search(None, "FROM \"boss@example.com\"")
    uid_list = uids[0].split()
    _, data = mail.fetch(uid_list[-1], "(RFC822)")
    # data[0][1] is the raw RFC822 message bytes
```

IMAP search strings follow a specific syntax (RFC 3501):
- `ALL` — all messages
- `FROM "x@y.com"` — from a specific sender
- `SUBJECT "keyword"` — subject contains keyword
- `SINCE 01-Jan-2025` — received after a date
- `UNSEEN` — unread messages
- Combine: `FROM "x@y.com" SUBJECT "roadmap"` — both conditions

### Decoding email headers

Email headers (like Subject) can be encoded in various charsets using RFC 2047 encoding:
`=?UTF-8?B?[base64]?=` or `=?ISO-8859-1?Q?[quoted-printable]?=`. The `email.header.decode_header`
function handles these encodings:

```python
from email.header import decode_header
raw, encoding = decode_header(msg["Subject"])[0]
subject = raw.decode(encoding or "utf-8") if isinstance(raw, bytes) else raw
```

### The email allow-list guard

Allowing an AI to send emails to arbitrary addresses is dangerous. A prompt injection attack
could make the agent email sensitive internal discussion to an external address. The guard:
1. Extract all email addresses from `employees.md` using regex
2. Before any `send_email` call, check that all recipients are in this set
3. If any unknown address is found, reject the call with an error message
4. The agent is instructed to `search_context` for the address first, then retry

This limits the blast radius: even if the agent is manipulated, it can only email known
internal addresses.

---

## In this project

**Send function:** `core/email_service.py` — `send_or_log()`, lines ~25–52. Degrades gracefully:
if `GMAIL_SENDER` / `GMAIL_APP_PASSWORD` are not set, writes to `outputs/email_log.txt` with
mode `[SIMULATED]` instead of `[SENT]`. No crash, no silent failure.

**Read function:** `core/email_service.py` — `read_inbox()`, lines ~60–106. Returns a list of
dicts with `{sender, subject, date, body_snippet}`. Handles multipart messages (walks MIME parts,
prefers `text/plain`, falls back to `text/html` stripped of tags). Returns an error dict if
credentials are not configured.

**HTML stripping:** `core/email_service.py` — `_strip_html()`, lines ~55–57. Removes all HTML
tags with regex and collapses whitespace. Used when an email has no plain-text part.

**Allow-list guard:** `core/tools.py` — `_known_emails()`, lines ~10–16, and the guard in
`run_tool("send_email", ...)`, lines ~182–193. Rejects any recipient not found in `employees.md`.

**Artifact notification builder:** `core/email_service.py` — `_artifact_email_body()`, lines
~109–128. Dynamically builds the email body from the artifacts dict. Each section is included
up to 1,200 characters. The order follows the `LABELS` dict:
Roadmap → Key Focus Areas → Requirements → Success Metrics → Impact Quadrant → RICE Score.

**`notify_artifacts_generated()`:** `core/email_service.py` lines ~130–136. Called from `app.py`
immediately after `save_artifacts()`. Reads recipients and subject from
`config/email_config.yaml`, builds the body dynamically, calls `send_or_log()`.

**`read_inbox` as a tool:** `core/tools.py` lines ~174–179 and the tool definition at lines
~59–88. The agent can call it with any IMAP search string. Returns JSON-serialised list of
email summaries injected as a tool result into the model's context.

**Configuration:** `config/email_config.yaml`. Stores recipient lists and subject templates.
The body template in this file is now **ignored** — `_artifact_email_body()` generates the body
dynamically. Only `recipients` and `subject` are read from the config.

**Environment variables:** `.env` file (not committed to git).
- `GMAIL_SENDER` — your Gmail address
- `GMAIL_APP_PASSWORD` — the 16-character app password
