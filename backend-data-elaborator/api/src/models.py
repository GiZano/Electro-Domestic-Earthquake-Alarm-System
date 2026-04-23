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
    city = Column(String(100), nullable=False)

    # Relationships
    misurators = relationship("Misurator", back_populates="zone", cascade="all, delete-orphan")


class Misurator(Base):
    """
    IoT Sensor Device.
    Includes Security (ECDSA Key) and Hardware Identity (MAC, Firmware).
    """
    __tablename__ = "misurators"

    id = Column(Integer, primary_key=True, index=True)
    active = Column(Boolean, default=True, nullable=False)
    
    # Foreign Key
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)

    # --- GPS Configuration ---
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    location = Column(Geometry('POINT', srid=4326), nullable=True)

    # --- SECURITY & IDENTITY ---
    # La chiave pubblica è l'identità crittografica primaria
    public_key_hex = Column(String, nullable=False, unique=True, index=True)
    
    # [FIX CRITICO] Identificativi Hardware per il Provisioning
    mac_address = Column(String(17), nullable=True, unique=True, index=True)
    firmware_version = Column(String(20), nullable=True)

    # Relationships
    zone = relationship("Zone", back_populates="misurators")
    misurations = relationship("Misuration", back_populates="misurator", cascade="all, delete-orphan")


class Misuration(Base):
    __tablename__ = "misurations"

    id = Column(Integer, primary_key=True, index=True)
    recorded_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)
    value = Column(Integer, nullable=False)
    
    misurator_id = Column(Integer, ForeignKey("misurators.id"), nullable=False)

    misurator = relationship("Misurator", back_populates="misurations")


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("zones.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    severity = Column(Float, nullable=False) 
    message = Column(String(255), nullable=True)

    zone = relationship("Zone")