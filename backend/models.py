from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from backend.database import Base
from datetime import datetime

class Station(Base):
    __tablename__ = "stations"
    
    station_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand = Column(String(100), nullable=False)
    city = Column(String(100), nullable=False)
    address = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    prices = relationship("FuelPrice", back_populates="station")

class FuelPrice(Base):
    __tablename__ = "fuel_prices"
    
    price_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    station_id = Column(UUID(as_uuid=True), ForeignKey("stations.station_id", ondelete="CASCADE"))
    fuel_type = Column(String(50), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    reported_at = Column(DateTime)
    scraped_at = Column(DateTime, default=datetime.utcnow)
    
    station = relationship("Station", back_populates="prices")
