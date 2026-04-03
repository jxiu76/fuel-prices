import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from scraper import fetch_fuel_prices

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scheduled_job():
    logging.info("Starting scheduled extraction job...")
    
    # 1. Extract
    data = fetch_fuel_prices()
    
    if not data:
        logging.warning("No data retrieved during this run. Aborting pipeline step.")
        return
        
    # 2. Transform & Load
    # TODO: Connect to PostgreSQL and load the 'data'
    logging.info("Data extraction complete. Pending database insert.")

if __name__ == "__main__":
    scheduler = BlockingScheduler()
    
    # Schedule to run at 06:00 and 18:00 every day
    scheduler.add_job(scheduled_job, 'cron', hour='6,18')
    
    logging.info("Fuel Price Scraper Pipeline scheduled. Running every 12 hours (6 AM / 6 PM).")
    logging.info("Press Ctrl+C to stop.")
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logging.info("Scheduler cleanly terminated.")
