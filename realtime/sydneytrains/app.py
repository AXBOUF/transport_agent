"""
Sydney Trains Real-Time Data Scheduler
Schedules jobs to fetch sydney trains alerts, updates, and vehicle positions
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging
import time

from get_trip_alert import fetch_sydneytrains_alerts
from get_trip_update import fetch_sydneytrains_updates
from get_vehicle_pos import fetch_sydneytrains_positions

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pg_writer import snapshot_delay_history

def _snapshot():
    snapshot_delay_history("sydneytrains")

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_scheduler():
    """Initialize and configure the APScheduler.

    Intervals and stagger are set to stay within the Transport NSW API limits:
    20,000 calls/day and 5 calls/second across all feeds.
    Sydney Trains slot: updates at T+0s, positions at T+10s each 60s cycle.
    """
    scheduler = BackgroundScheduler()

    # Alerts - every 10 minutes (low frequency, data changes slowly)
    scheduler.add_job(
        func=fetch_sydneytrains_alerts,
        trigger="interval",
        seconds=600,
        id='sydneytrains_alerts_job',
        name='Fetch Sydney Trains Alerts',
        replace_existing=True,
    )

    # Trip updates - every 60s, fires immediately at start
    scheduler.add_job(
        func=fetch_sydneytrains_updates,
        trigger="interval",
        seconds=60,
        id='sydneytrains_updates_job',
        name='Fetch Sydney Trains Updates',
        replace_existing=True,
    )

    # Vehicle positions - every 60s, staggered 10s after updates
    scheduler.add_job(
        func=fetch_sydneytrains_positions,
        trigger="interval",
        seconds=60,
        start_date=datetime.now() + timedelta(seconds=10),
        id='sydneytrains_positions_job',
        name='Fetch Sydney Trains Positions',
        replace_existing=True,
    )

    # Delay history snapshot — every 5 minutes, staggered 30s after start
    scheduler.add_job(
        func=_snapshot,
        trigger="interval",
        seconds=300,
        start_date=datetime.now() + timedelta(seconds=30),
        id='sydneytrains_delay_history_job',
        name='Snapshot Sydney Trains Delay History',
        replace_existing=True,
    )

    scheduler.start()
    logger.info("✅ Sydney Trains scheduler started successfully")
    
    return scheduler

if __name__ == "__main__":
    scheduler = init_scheduler()
    
    try:
        # Keep the scheduler running
        print(f"🚆 Sydney Trains Real-Time Scheduler started at {datetime.now()}")
        print("Press Ctrl+C to exit")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        print("✅ Scheduler stopped")
