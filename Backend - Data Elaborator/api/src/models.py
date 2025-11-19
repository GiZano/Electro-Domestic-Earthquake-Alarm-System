from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from src.database import Base

class Zone(Base):
    __tablename__ = "zones"

    id   = Column(Integer, primary_key=True, index=True)
    city = Column(String(100), nullable=False)

class Misurator(Base):
    __tablename__ = "misurators"

    id      = Column(Integer, primary_key=True, index=True)
    active  = Column(Boolean, nullable=False)
    zone_id = Column(Integer, nullable=False)

class Misuration(Base):
    __tablename__ = "misurations"

    id           = Column(Integer, primary_key=True, index=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    value        = Column(Integer, nullable=False)
    misurator_id = Column(Integer, nullable=False)

