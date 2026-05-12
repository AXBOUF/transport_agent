"""
Buses Real-Time Data Scheduler
Schedules jobs to fetch buses alerts, updates, and vehicle positions
"""
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import logging

from get_trip_alert import fetch_buses_alerts
from get_trip_update import fetch_buses_updates
from get_vehicle_pos import fetch_buses_positions

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def init_scheduler():
    """Initialize and configure the APScheduler"""
    scheduler = BackgroundScheduler()
    
    # Alerts - every 10 minutes
    scheduler.add_job(
        func=fetch_buses_alerts,
        trigger="interval",
        seconds=600,
        id='buses_alerts_job',
        name='Fetch Buses Alerts',
        replace_existing=True,
    )

    # Trip updates - every 120s (buses feed is large, fetch takes >60s)
    scheduler.add_job(
        func=fetch_buses_updates,
        trigger="interval",
        seconds=120,
        start_date=datetime.now() + timedelta(seconds=20),
        id='buses_updates_job',
        name='Fetch Buses Updates',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )

    # Vehicle positions - every 120s, staggered 60s after updates
    scheduler.add_job(
        func=fetch_buses_positions,
        trigger="interval",
        seconds=120,
        start_date=datetime.now() + timedelta(seconds=80),
        id='buses_positions_job',
        name='Fetch Buses Positions',
        replace_existing=True,
        coalesce=True,
        max_instances=1,
    )
    
    scheduler.start()
    logger.info("✅ Buses scheduler started successfully")
    
    return scheduler

if __name__ == "__main__":
    scheduler = init_scheduler()
    
    try:
        # Keep the scheduler running
        print(f"🚌 Buses Real-Time Scheduler started at {datetime.now()}")
        print("Press Ctrl+C to exit")
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        print("✅ Scheduler stopped")
