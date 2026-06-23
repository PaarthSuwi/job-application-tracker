# sheets_manager.py - all Google Sheets read/write operations

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import SPREADSHEET_NAME, SHEET_COLUMNS, STATUS, GHOST_THRESHOLD_DAYS

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]


def get_client():
    creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
    return gspread.authorize(creds)


def get_or_create_sheet():
    client = get_client()
    try:
        sh = client.open(SPREADSHEET_NAME)
    except gspread.SpreadsheetNotFound:
        sh = client.create(SPREADSHEET_NAME)
        print(f"Created new spreadsheet: {SPREADSHEET_NAME}")
    worksheet = sh.sheet1
    existing = worksheet.row_values(1)
    if existing != SHEET_COLUMNS:
        worksheet.clear()
        worksheet.append_row(SHEET_COLUMNS)
        print("Headers written to sheet.")
    return worksheet


def get_all_applications():
    worksheet = get_or_create_sheet()
    records = worksheet.get_all_records()
    if not records:
        return pd.DataFrame(columns=SHEET_COLUMNS)
    return pd.DataFrame(records)


def application_exists(company: str, role: str) -> bool:
    df = get_all_applications()
    if df.empty:
        return False
    match = df[
        (df['Company'].str.lower() == company.lower()) &
        (df['Role'].str.lower() == role.lower())
    ]
    return not match.empty


def add_application(company: str, role: str, source: str = "",
                    job_link: str = "", status: str = None,
                    notes: str = "", email_subject: str = ""):
    if status is None:
        status = STATUS["APPLIED"]
    if application_exists(company, role):
        print(f"Already tracked: {company} - {role}")
        return False
    worksheet = get_or_create_sheet()
    today = datetime.today().strftime('%Y-%m-%d')
    row = [
        today, company, role, source, job_link,
        status, today, "", notes, email_subject
    ]
    worksheet.append_row(row)
    print(f"Added: {company} - {role} [{status}]")
    return True


def update_application_status(company: str, role: str, new_status: str,
                               notes: str = "", response_date: str = "",
                               email_subject: str = ""):
    worksheet = get_or_create_sheet()
    df = get_all_applications()
    if df.empty:
        return False

    today = datetime.today().strftime('%Y-%m-%d')
    mask = (
        (df['Company'].str.lower() == company.lower()) &
        (df['Role'].str.lower() == role.lower())
    )
    matched = df[mask]
    if matched.empty:
        print(f"Not found: {company} - {role}")
        return False

    row_index = matched.index[0] + 2
    priority = [
        STATUS["APPLIED"], STATUS["SHORTLISTED"], STATUS["INTERVIEW"],
        STATUS["OFFER"], STATUS["REJECTED"], STATUS["GHOSTED"]
    ]
    current_status = df.loc[matched.index[0], 'Status']

    if current_status in priority and new_status in priority:
        if priority.index(new_status) <= priority.index(current_status):
            if new_status not in [STATUS["REJECTED"], STATUS["GHOSTED"]]:
                print(f"Skipping downgrade: {company} stays at '{current_status}'")
                return False

    col_map = {col: idx + 1 for idx, col in enumerate(SHEET_COLUMNS)}
    worksheet.update_cell(row_index, col_map['Status'], new_status)
    worksheet.update_cell(row_index, col_map['Last Updated'], today)
    if response_date:
        worksheet.update_cell(row_index, col_map['Response Date'], response_date)
    if notes:
        existing_notes = df.loc[matched.index[0], 'Notes']
        new_notes = f"{existing_notes} | {notes}" if existing_notes else notes
        worksheet.update_cell(row_index, col_map['Notes'], new_notes)
    if email_subject:
        worksheet.update_cell(row_index, col_map['Email Subject'], email_subject)

    print(f"Updated: {company} - {role} -> {new_status}")
    return True


def mark_ghosted_applications(days_threshold: int = None):
    if days_threshold is None:
        days_threshold = GHOST_THRESHOLD_DAYS
    worksheet = get_or_create_sheet()
    df = get_all_applications()
    if df.empty:
        return
    today = datetime.today()
    for i, row in df.iterrows():
        if row['Status'] == STATUS["APPLIED"]:
            try:
                applied_date = datetime.strptime(row['Date Applied'], '%Y-%m-%d')
                days_elapsed = (today - applied_date).days
                if days_elapsed >= days_threshold:
                    row_index = i + 2
                    col_map = {col: idx + 1 for idx, col in enumerate(SHEET_COLUMNS)}
                    worksheet.update_cell(row_index, col_map['Status'], STATUS["GHOSTED"])
                    worksheet.update_cell(
                        row_index, col_map['Last Updated'],
                        today.strftime('%Y-%m-%d')
                    )
                    print(f"Ghosted: {row['Company']} - {row['Role']} ({days_elapsed} days)")
            except Exception:
                continue
