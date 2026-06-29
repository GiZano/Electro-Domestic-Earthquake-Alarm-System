"""
Database Models Definition
--------------------------
Defines the SQLAlchemy ORM models.
Updated to support Device Provisioning (MAC Address & Firmware Version).
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from src.database import Base

class Zone(Base):
    __tablename__ = "zones"

    id = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False, unique=True)
    
    # Auditability timestamp
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    
    # PostGIS Polygon boundary for automatic sensor assignment
    geom = Column(Geometry('POLYGON', srid=4326), nullable=True)

    # Relationships
    sensors = relationship("Sensor", back_populates="zone", cascade="all, delete-orphan")


class Sensor(Base):
    """
    IoT Sensor Device.
    Includes Security (ECDSA Key) and Hardware Identity (MAC, Firmware).
    """
    __tablename__ = "sensors"

    id = Column(Integer, primary_key=True, index=True)
    active = Column(Boolean, default=True, nullable=False)
    
    # Foreign Key
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    # --- GPS Configuration ---
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)

    # --- SECURITY & IDENTITY ---
    # The public key is the primary cryptographic identity
    public_key_hex = Column(String, nullable=False, unique=True, index=True)
    
    # [CRITICAL FIX] Hardware identifiers for Provisioning
    mac_address = Column(String(17), nullable=True, unique=True, index=True)
    firmware_version = Column(String(20), nullable=True)

    # Relationships
    zone = relationship("Zone", back_populates="sensors")
    readings = relationship("Reading", back_populates="sensor", cascade="all, delete-orphan")


class Reading(Base):
    __tablename__ = "readings"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    value = Column(Integer, nullable=False)
    
    sensor_id = Column(Integer, ForeignKey("sensors.id"), nullable=False)

    sensor = relationship("Sensor", back_populates="readings")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    severity = Column(Float, nullable=False) 
    message = Column(String(255), nullable=True)

    zone = relationship("Zone")