# gmail_scanner.py - scans Gmail for job-related emails

import os
import base64
import re
import json
import tempfile
from datetime import datetime, timedelta
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from sheets_manager import (
    add_application, update_application_status,
    get_all_applications, application_exists
)
from config import (
    POSITIVE_KEYWORDS, REJECTION_KEYWORDS, APPLIED_KEYWORDS,
    DAYS_TO_SCAN_BACK, STATUS
)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
PROCESSED_IDS_FILE = "processed_email_ids.json"

def get_gmail_service():
    creds = None

    # Try Streamlit secrets first (cloud deployment)
    try:
        import streamlit as st

        # Load token from secrets if available
        if "gmail_token" in st.secrets:
            token_data = dict(st.secrets["gmail_token"])
            creds = Credentials.from_authorized_user_info(token_data, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                return build('gmail', 'v1', credentials=creds)

        if creds and creds.valid:
            return build('gmail', 'v1', credentials=creds)

    except Exception:
        pass

    # Local fallback: use token.json or run OAuth flow
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'gmail_oauth_credentials.json', SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def load_processed_ids():
    if os.path.exists(PROCESSED_IDS_FILE):
        with open(PROCESSED_IDS_FILE, 'r') as f:
            return set(json.load(f))
    return set()

def save_processed_ids(ids: set):
    with open(PROCESSED_IDS_FILE, 'w') as f:
        json.dump(list(ids), f)

def decode_body(payload):
    body = ""
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                data = part['body'].get('data', '')
                if data:
                    body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
            elif part['mimeType'] == 'multipart/alternative':
                body += decode_body(part)
    elif payload['mimeType'] == 'text/plain':
        data = payload['body'].get('data', '')
        if data:
            body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
    return body

def extract_company_from_email(sender: str, subject: str, body: str) -> str:
    email_match = re.search(r'@([w.-]+)', sender)
    if email_match:
        domain = email_match.group(1)
        generic = [
            'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
            'noreply.com', 'notifications.com', 'mail.com', 'zoho.com'
        ]
        if not any(g in domain for g in generic):
            company = domain.split('.')[0].replace('-', ' ').title()
            return company
    name_match = re.match(r'^"?([^"<]+)"?\s*<', sender)
    if name_match:
        name = name_match.group(1).strip()
        name = re.sub(
            r'\b(careers|recruiting|hr|talent|team|noreply|jobs|no-reply)\b',
            '', name, flags=re.IGNORECASE
        ).strip()
        if name and len(name) > 2:
            return name.title()
    return "Unknown Company"

def extract_role_from_subject(subject: str) -> str:
    patterns = [
        r'(?:application for|applying for|role of|position of|regarding)\s+(.+?)(?:\s+at\s+|\s*$)',
        r'(?:re:|fw:)\s*(?:your application[:\s-]*)(.+?)(?:\s+at\s+|\s*[-|]\s*|\s*$)',
    ]
    for pattern in patterns:
        match = re.search(pattern, subject, re.IGNORECASE)
        if match and match.lastindex:
            return match.group(1).strip().title()[:80]
    return subject[:60].title()

def classify_email(subject: str, body: str):
    text = (subject + " " + body).lower()
    for kw in APPLIED_KEYWORDS:
        if kw.lower() in text:
            return 'applied', kw
    for kw in POSITIVE_KEYWORDS:
        if kw.lower() in text:
            return 'positive', kw
    for kw in REJECTION_KEYWORDS:
        if kw.lower() in text:
            return 'rejection', kw
    return None, None

def scan_gmail(days_back: int = None):
    if days_back is None:
        days_back = DAYS_TO_SCAN_BACK

    print(f"\nScanning Gmail for last {days_back} days...")
    service = get_gmail_service()
    processed_ids = load_processed_ids()

    after_date = (datetime.today() - timedelta(days=days_back)).strftime('%Y/%m/%d')
    query = f"after:{after_date}"

    results = service.users().messages().list(
        userId='me', q=query, maxResults=500
    ).execute()
    messages = results.get('messages', [])
    print(f"Found {len(messages)} emails to process.")

    new_count = 0
    update_count = 0
    skipped_count = 0

    for msg_meta in messages:
        msg_id = msg_meta['id']
        if msg_id in processed_ids:
            skipped_count += 1
            continue
        try:
            msg = service.users().messages().get(
                userId='me', id=msg_id, format='full'
            ).execute()
            headers = {h['name']: h['value'] for h in msg['payload']['headers']}
            subject = headers.get('Subject', '')
            sender = headers.get('From', '')

            body = decode_body(msg['payload'])
            category, keyword = classify_email(subject, body)

            if category is None:
                processed_ids.add(msg_id)
                continue

            company = extract_company_from_email(sender, subject, body)
            role = extract_role_from_subject(subject)
            today = datetime.today().strftime('%Y-%m-%d')

            print(f"  [{category.upper()}] {company} - {role}")
            print(f"  Subject: {subject[:80]}")

            if category == 'applied':
                if not application_exists(company, role):
                    add_application(
                        company=company, role=role, source="Email/Auto",
                        status=STATUS["APPLIED"],
                        notes="Auto-detected from email", email_subject=subject
                    )
                    new_count += 1

            elif category == 'positive':
                offer_kws = ["offer letter", "job offer", "pleased to offer"]
                interview_kws = ["interview", "schedule a call", "technical round",
                                 "hr round", "assessment", "next steps"]

                if any(kw in (subject + " " + body).lower() for kw in offer_kws):
                    new_status = STATUS["OFFER"]
                elif any(kw in (subject + " " + body).lower() for kw in interview_kws):
                    new_status = STATUS["INTERVIEW"]
                else:
                    new_status = STATUS["SHORTLISTED"]

                if application_exists(company, role):
                    result = update_application_status(
                        company, role, new_status,
                        response_date=today, email_subject=subject
                    )
                    if result:
                        update_count += 1
                else:
                    add_application(
                        company=company, role=role, source="Email/Auto",
                        status=new_status,
                        notes="Auto-detected positive response", email_subject=subject
                    )
                    new_count += 1

            elif category == 'rejection':
                if application_exists(company, role):
                    result = update_application_status(
                        company, role, STATUS["REJECTED"],
                        response_date=today, email_subject=subject
                    )
                    if result:
                        update_count += 1
                else:
                    add_application(
                        company=company, role=role, source="Email/Auto",
                        status=STATUS["REJECTED"],
                        notes="Auto-detected rejection", email_subject=subject
                    )
                    new_count += 1

            processed_ids.add(msg_id)

        except Exception as e:
            print(f"  Error processing message {msg_id}: {e}")
            continue

    save_processed_ids(processed_ids)
    print(f"\nDone! New: {new_count}, Updated: {update_count}, Skipped: {skipped_count}")
    return new_count, update_count

if __name__ == "__main__":
    scan_gmail()
