# config.py - central configuration for all modules

SPREADSHEET_NAME = "Job Application Tracker"

SCAN_INTERVAL_MINUTES = 30
DAYS_TO_SCAN_BACK = 90

POSITIVE_KEYWORDS = [
    "interview", "shortlisted", "next steps", "pleased to inform",
    "we would like to invite", "schedule a call", "move forward",
    "selected", "congratulations", "offer letter", "job offer",
    "pleased to offer", "we are happy to", "further process",
    "assessment", "technical round", "hr round", "aptitude test",
    "next round", "proceed further", "happy to inform",
]

REJECTION_KEYWORDS = [
    "regret", "unfortunately", "not moving forward", "not selected",
    "other candidates", "not shortlisted", "we have decided",
    "does not match", "filled the position", "no longer considering",
    "not proceed", "not a fit", "position has been filled",
    "not successful", "keep your resume on file", "not be moving forward",
    "will not be proceeding", "not been selected",
]

APPLIED_KEYWORDS = [
    "application received", "thank you for applying", "we received your application",
    "application confirmation", "successfully applied", "your application has been",
    "application submitted", "we have received your", "thank you for your interest",
    "your application for", "applied successfully",
]

SHEET_COLUMNS = [
    "Date Applied", "Company", "Role", "Source", "Job Link",
    "Status", "Last Updated", "Response Date", "Notes", "Email Subject"
]

STATUS = {
    "APPLIED":      "Applied",
    "SHORTLISTED":  "Shortlisted",
    "INTERVIEW":    "Interview Scheduled",
    "OFFER":        "Offer Received",
    "REJECTED":     "Rejected",
    "GHOSTED":      "Ghosted",
    "WITHDRAWN":    "Withdrawn",
}

GHOST_THRESHOLD_DAYS = 21
