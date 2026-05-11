"""
Metro Real-Time Data Scheduler
Schedules jobs to fetch metro alerts, updates, and vehicle positions
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import logging

from get_trip_alert import fetch_metro_alerts
from get_trip_update import fetch_metro_updates
from get_vehicle_pos import fetch_metro_positions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_scheduler():
    """Initialize and configure the APScheduler"""
    scheduler = BackgroundScheduler()
    
    # Schedule metro alerts - every 10 minutes
    scheduler.add_job(
        func=fetch_metro_alerts,
        trigger="interval",
        seconds=600,
        id='metro_alerts_job',
        name='Fetch Metro Alerts',
        replace_existing=True
    )
    
    # Schedule metro updates - every 30 seconds
    scheduler.add_job(
        func=fetch_metro_updates,
        trigger="interval",
        seconds=30,
        id='metro_updates_job',
        name='Fetch Metro Updates',
        replace_existing=True
    )
    
    # Schedule metro vehicle positions - every 30 seconds
    scheduler.add_job(
        func=fetch_metro_positions,
        trigger="interval",
        seconds=30,
        id='metro_positions_job',
        name='Fetch Metro Positions',
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("✅ Metro scheduler started successfully")
    
    return scheduler

if __name__ == "__main__":
    scheduler = init_scheduler()
    
    try:
        # Keep the scheduler running
        print(f"🚆 Metro Real-Time Scheduler started at {datetime.now()}")
        print("Press Ctrl+C to exit")
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        print("✅ Scheduler stopped")