import os
import time
import random
import logging
from datetime import datetime
from playwright.sync_api import sync_playwright
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import our models
from backend import models

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL) if DATABASE_URL else None
SessionLocal = sessionmaker(bind=engine) if engine else None

# List of GasWatchPH city paths to scrape (Focusing on Quezon City to optimize resources)
CITIES = ["quezon-city"]

def scrape_real_fuel_prices():
    prices_data = []
    
    with sync_playwright() as p:
        logging.info("Bringing up Playwright browser...")
        # Cloud environments (Render/Docker) prohibit Chromium from running without these specific sandbox bypass flags
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu"
            ]
        )
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        )
        
        for city in CITIES:
            url = f"https://gaswatchph.com/{city}"
            logging.info(f"Navigating to {url}")
            
            try:
                # Use domcontentloaded instead of networkidle so background analytics/ads don't trigger the 30s timeout
                page.goto(url, wait_until="domcontentloaded", timeout=60000)
                delay = random.uniform(2, 5)
                logging.info(f"Rate Limiting active. Sleeping for {delay:.2f} seconds before parsing...")
                time.sleep(delay)
                
                # Wait for the JS table to inject (Extended timeout for slow free-tier container)
                page.wait_for_selector("table.station-table tbody tr", timeout=60000)
                
                # Automatically click "Show all 239 stations..." to unlock massive dataset!
                try:
                    expand_buttons = page.get_by_text("Show all", exact=False).all()
                    for btn in expand_buttons:
                        if btn.is_visible():
                            logging.info("Found 'Show all stations' button! Clicking to unleash data...")
                            btn.click()
                            time.sleep(4) # Wait briefly for the DOM to inject all 200+ rows
                            break
                except Exception as btn_err:
                    logging.warning(f"Could not interact with 'Show all' button (It might not exist here): {btn_err}")
                
                rows = page.locator("table.station-table tbody tr").all()
                for row in rows:
                    station_info = row.locator("td div.station-info").inner_text()
                    price_text = row.locator("td.price-col").inner_text()
                    
                    import re
                    brand = station_info.split(" ")[0].capitalize() 
                    fuel_type = "Diesel" # GasWatch Defaults to Diesel tab on load
                    
                    # Robust RegEx to extract only the numeric price, ignoring text like "actual"
                    price_match = re.search(r"(\d+(?:\.\d+)?)", price_text.replace(",", ""))
                    price_clean = float(price_match.group(1)) if price_match else 0.0
                    
                    prices_data.append({
                        "brand": brand,
                        "city": city.replace("-", " ").title(),
                        "fuel_type": fuel_type,
                        "price": price_clean,
                        "latitude": 14.6, # Approximate until Geocoded
                        "longitude": 121.0
                    })
            except Exception as e:
                logging.error(f"Error extracting data for {city}: {e}")
                
        browser.close()
        
    return prices_data

def process_and_store(data):
    if not SessionLocal:
        logging.warning("DATABASE_URL is missing! Printing locally instead of saving:")
        for r in data: print(r)
        return
        
    db = SessionLocal()
    count = 0
    logging.info("Uploading fresh data to PostgreSQL...")
    for record in data:
        station_q = db.query(models.Station).filter(
            models.Station.brand == record["brand"],
            models.Station.city == record["city"]
        ).first()
        
        if not station_q:
            station_q = models.Station(brand=record["brand"], city=record["city"], latitude=record["latitude"], longitude=record["longitude"])
            db.add(station_q)
            db.flush()
            
        fuel_price = models.FuelPrice(
            station_id=station_q.station_id,
            fuel_type=record["fuel_type"],
            price=record["price"],
            reported_at=datetime.utcnow()
        )
        db.add(fuel_price)
        count += 1
        
    db.commit()
    logging.info(f"✅ Successfully inserted {count} LIVE price records into the database.")

if __name__ == "__main__":
    logging.info("Initiating Live Data Pipeline Scrape...")
    live_data = scrape_real_fuel_prices()
    process_and_store(live_data)
