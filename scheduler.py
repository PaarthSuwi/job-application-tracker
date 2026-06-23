# scheduler.py - auto-runs Gmail scanner on a schedule

import schedule
import time
import logging
from datetime import datetime
from gmail_scanner import scan_gmail
from sheets_manager import mark_ghosted_applications
from config import SCAN_INTERVAL_MINUTES, GHOST_THRESHOLD_DAYS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('scheduler.log'), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


def run_scan():
    try:
        logger.info(f"Auto-scan at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        new_count, update_count = scan_gmail(days_back=7)
        logger.info(f"Done: {new_count} new, {update_count} updated")
        mark_ghosted_applications(days_threshold=GHOST_THRESHOLD_DAYS)
    except Exception as e:
        logger.error(f"Scan failed: {e}", exc_info=True)


if __name__ == '__main__':
    logger.info(f"Scheduler started - scanning every {SCAN_INTERVAL_MINUTES} minutes.")
    run_scan()
    schedule.every(SCAN_INTERVAL_MINUTES).minutes.do(run_scan)
    while True:
        schedule.run_pending()
        time.sleep(30)
