# Job Application Tracker

A live, self-updating job application tracker with **Gmail auto-scanning**, **Google Sheets cloud storage**, and a **Streamlit web dashboard** with self-analysis insights.

---

## Features

- **Gmail Auto-Scanner** - Automatically detects applied/shortlisted/interview/rejection emails using keyword matching
- **Google Sheets Database** - All your application data stored in the cloud, accessible anywhere
- **Streamlit Dashboard** - Live web dashboard with charts, filters, and intelligent recommendations
- **Auto-Ghosted Detection** - Applications with no response after 21 days are automatically marked as Ghosted
- **CLI Tool** - Manually add or update applications from the terminal
- **Auto-Scheduler** - Runs Gmail scan every 30 minutes in the background

---

## Project Structure

```
job-application-tracker/
├── app.py                  # Streamlit web dashboard
├── gmail_scanner.py        # Gmail API auto-scanner
├── sheets_manager.py       # Google Sheets read/write
├── tracker.py              # CLI to add/update applications
├── scheduler.py            # Auto-runs scanner every N minutes
├── config.py               # Central configuration (keywords, settings)
├── requirements.txt        # Python dependencies
├── credentials.json        # (YOU provide) Google Service Account key
├── gmail_oauth_credentials.json  # (YOU provide) Gmail OAuth credentials
└── token.json              # (auto-generated) Gmail OAuth token
```

---

## Setup Guide

### Step 1: Clone the Repository

```bash
git clone https://github.com/PaarthSuwi/job-application-tracker.git
cd job-application-tracker
pip install -r requirements.txt
```

### Step 2: Google Cloud Setup (One-Time)

You need **two** credential files from Google Cloud Console.

#### 2a. Service Account (for Google Sheets)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project (or use existing)
3. Enable **Google Sheets API** and **Google Drive API**
4. Go to **Credentials** > **Create Credentials** > **Service Account**
5. Download the JSON key file
6. Rename it to `credentials.json` and place in the project folder
7. Open [Google Sheets](https://sheets.google.com) and share the sheet (created automatically by the app) with the service account email (found in the JSON file)

#### 2b. OAuth Credentials (for Gmail)

1. In the same project, go to **Credentials** > **Create Credentials** > **OAuth 2.0 Client IDs**
2. Application type: **Desktop App**
3. Download the JSON
4. Rename it to `gmail_oauth_credentials.json` and place in project folder
5. Enable **Gmail API** in the Cloud Console

### Step 3: First Run (Authenticate Gmail)

```bash
python gmail_scanner.py
```

A browser window will open asking you to authorize Gmail access. After authorizing, `token.json` will be created automatically and stored for future runs.

---

## Usage

### Run the Web Dashboard

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

### Run the Auto-Scanner (Background)

```bash
python scheduler.py
```

Scans Gmail every 30 minutes and auto-updates the sheet.

### CLI - Add Application Manually

```bash
python tracker.py add --company Google --role "Software Engineer" --source LinkedIn
python tracker.py add --company Infosys --role "SDE-1" --source Naukri --link "https://..."
```

### CLI - Update Application Status

```bash
python tracker.py update --company Google --role "Software Engineer" --status "Interview Scheduled"
python tracker.py update --company Infosys --role "SDE-1" --status "Rejected"
```

### CLI - Mark Ghosted

```bash
python tracker.py ghost           # default 21 days
python tracker.py ghost --days 14 # custom threshold
```

---

## Gmail Keyword Detection

The scanner classifies emails into 3 categories:

| Category | Examples |
|---|---|
| **Application Confirmed** | "application received", "thank you for applying" |
| **Positive Response** | "interview", "shortlisted", "offer letter", "assessment" |
| **Rejection** | "regret", "not moving forward", "unfortunately" |

Edit keywords in `config.py` to customise for your needs.

---

## Dashboard Panels

- **KPI Row** - Total applied, response rate %, active applications, interview count, offer count
- **Status Pie Chart** - Visual breakdown of where all applications stand
- **Applications Over Time** - Weekly application trend line chart
- **Top Sources** - Which job portals you've applied through most
- **Source Response Rate** - Which portals give best callbacks (colour coded)
- **Self-Analysis Insights** - Smart recommendations based on your data
- **Filterable Table** - Search/filter all applications by status, source, date range

---

## Deploy to Streamlit Cloud (Free)

1. Push this repo to GitHub (done!)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repo and `app.py` as the main file
5. Add your secrets in Streamlit Cloud settings (`credentials.json` contents as a secret)

---

## Environment Variables (Optional)

You can set these in a `.env` file:

```
SPREADSHEET_NAME=Job Application Tracker
SCAN_INTERVAL_MINUTES=30
```

---

## License

MIT - Feel free to use and modify for your own job search!
