"""
Quick test: send a sample email and read the first message in the inbox.
Run from the project root: python test_email.py
"""
import imaplib
import json
import os
import smtplib
import sys
from email import message_from_bytes
from email.header import decode_header
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from dotenv import load_dotenv

load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

SENDER = os.getenv("GMAIL_SENDER", "")
PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")
TEST_RECIPIENT = "126156054@sastra.ac.in"


def check_credentials():
    if not SENDER or not PASSWORD:
        print("ERROR: GMAIL_SENDER or GMAIL_APP_PASSWORD not set in .env")
        sys.exit(1)
    print(f"Credentials loaded — sending as: {SENDER}\n")


def send_test_email():
    print(f"--- Sending test email to {TEST_RECIPIENT} ---")
    msg = MIMEMultipart()
    msg["From"] = SENDER
    msg["To"] = TEST_RECIPIENT
    msg["Subject"] = "PM Assistant — Email Capability Test"
    body = (
        "Hi,\n\n"
        "This is an automated test from the Zepto PM Assistant to verify that "
        "outbound email sending is working correctly.\n\n"
        "If you received this, the Gmail SMTP integration is live.\n\n"
        "— PM Intelligence Layer"
    )
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as srv:
        srv.login(SENDER, PASSWORD)
        srv.sendmail(SENDER, [TEST_RECIPIENT], msg.as_string())

    print(f"  [OK] Email sent to {TEST_RECIPIENT}\n")


def read_first_inbox_email():
    print("--- Reading first (most recent) email in inbox ---")
    with imaplib.IMAP4_SSL("imap.gmail.com") as mail:
        mail.login(SENDER, PASSWORD)
        mail.select("inbox")
        _, uids = mail.search(None, "ALL")
        uid_list = uids[0].split()
        if not uid_list:
            print("  Inbox is empty.")
            return

        uid = uid_list[-1]  # most recent
        _, data = mail.fetch(uid, "(RFC822)")
        msg = message_from_bytes(data[0][1])

        raw_subject, enc = decode_header(msg["Subject"] or "")[0]
        subject = (
            raw_subject.decode(enc or "utf-8", errors="replace")
            if isinstance(raw_subject, bytes)
            else (raw_subject or "")
        )

        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode(errors="replace")
                    break
        else:
            body = msg.get_payload(decode=True).decode(errors="replace")

        print(f"  From   : {msg.get('From')}")
        print(f"  Subject: {subject}")
        print(f"  Date   : {msg.get('Date')}")
        print(f"\n  Body:\n{'-' * 50}")
        print(body.strip())
        print('-' * 50)


if __name__ == "__main__":
    check_credentials()
    send_test_email()
    read_first_inbox_email()
