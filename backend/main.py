from fastapi import FastAPI, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from backend import models, database
from datetime import datetime, timedelta
import logging

# Import scraper for free-tier integration
try:
    from scraper.scraper import scrape_real_fuel_prices, process_and_store
except ImportError:
    logging.warning("Scraper module not found or missing dependencies.")

# Create tables for dev environment
models.Base.metadata.create_all(bind=database.engine)

app = FastAPI(
    title="NCR Fuel Watch API",
    description="Backend API exposing historical and current fuel prices across Metro Manila.",
    version="1.0.0"
)

@app.get("/")
def read_root():
    return {"status": "ok", "message": "NCR Fuel Watch API is online."}

from threading import Lock

# Prevent multiple massive browser instances from OOMing the 512MB free tier container
scrape_lock = Lock()

@app.get("/api/admin/trigger-scrape")
def trigger_scrape(background_tasks: BackgroundTasks):
    """Bypasses paid Background Workers by running the scraper inside the free Web Service!"""
    if scrape_lock.locked():
        return {"message": "Whoops! A live scrape is already actively running right now. Please wait for it to finish so we don't crash the server!"}
        
    def run_pipeline():
        with scrape_lock:
            try:
                live_data = scrape_real_fuel_prices()
                process_and_store(live_data)
            except Exception as e:
                logging.error(f"Background scrape failed: {e}")
            
    background_tasks.add_task(run_pipeline)
    return {"message": "Live Data Pipeline successfully triggered natively in the background!"}

@app.get("/api/stations")
def get_stations(city: str = None, brand: str = None, db: Session = Depends(database.get_db)):
    """Retrieve active fuel stations, optionally filtered by city/brand."""
    query = db.query(models.Station)
    if city:
        query = query.filter(models.Station.city.ilike(f"%{city}%"))
    if brand:
        query = query.filter(models.Station.brand.ilike(f"%{brand}%"))
    return query.all()

@app.get("/api/prices/latest")
def get_latest_prices(city: str = None, fuel_type: str = None, db: Session = Depends(database.get_db)):
    """Retrieve the latest prices from the last 7 days for analytical mapping."""
    query = db.query(models.FuelPrice, models.Station).join(models.Station)
    
    if city:
        query = query.filter(models.Station.city.ilike(f"%{city}%"))
    if fuel_type:
        query = query.filter(models.FuelPrice.fuel_type.ilike(f"%{fuel_type}%"))
        
    recent_date = datetime.utcnow() - timedelta(days=7)
    query = query.filter(models.FuelPrice.scraped_at >= recent_date)
    
    results = query.all()
    
    payload = []
    for price, station in results:
        payload.append({
            "station_id": station.station_id,
            "brand": station.brand,
            "city": station.city,
            "lat": station.latitude,
            "lon": station.longitude,
            "fuel_type": price.fuel_type,
            "price": float(price.price),
            "reported_at": price.reported_at,
            "scraped_at": price.scraped_at
        })
    return payload
