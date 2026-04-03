-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Dimension Table: Stations in NCR
CREATE TABLE IF NOT EXISTS stations (
    station_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    brand VARCHAR(100) NOT NULL,
    city VARCHAR(100) NOT NULL,
    address TEXT,
    latitude FLOAT,
    longitude FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Fact Table: Scraping History of Fuel Prices
CREATE TABLE IF NOT EXISTS fuel_prices (
    price_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    station_id UUID REFERENCES stations(station_id) ON DELETE CASCADE,
    fuel_type VARCHAR(50) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    reported_at TIMESTAMP,
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for faster time-series queries
CREATE INDEX IF NOT EXISTS idx_fuel_prices_scraped_at ON fuel_prices(scraped_at);
CREATE INDEX IF NOT EXISTS idx_fuel_prices_station_fuel ON fuel_prices(station_id, fuel_type);
