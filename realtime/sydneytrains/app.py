"""
Sydney Trains Real-Time Data Scheduler
Schedules jobs to fetch sydney trains alerts, updates, and vehicle positions
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging
import time

from schema import init_db
from get_trip_alert import fetch_sydneytrains_alerts
from get_trip_update import fetch_sydneytrains_updates
from get_vehicle_pos import fetch_sydneytrains_positions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_scheduler():
    """Initialize and configure the APScheduler"""
    init_db()
    scheduler = BackgroundScheduler()
    
    # Schedule sydney trains alerts - every 10 minutes
    scheduler.add_job(
        func=fetch_sydneytrains_alerts,
        trigger="interval",
        seconds=600,
        id='sydneytrains_alerts_job',
        name='Fetch Sydney Trains Alerts',
        replace_existing=True
    )
    
    # Schedule sydney trains updates - every 30 seconds
    scheduler.add_job(
        func=fetch_sydneytrains_updates,
        trigger="interval",
        seconds=30,
        id='sydneytrains_updates_job',
        name='Fetch Sydney Trains Updates',
        replace_existing=True
    )
    
    # Schedule sydney trains vehicle positions - every 30 seconds
    scheduler.add_job(
        func=fetch_sydneytrains_positions,
        trigger="interval",
        seconds=30,
        id='sydneytrains_positions_job',
        name='Fetch Sydney Trains Positions',
        replace_existing=True
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
