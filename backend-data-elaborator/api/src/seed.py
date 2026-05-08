"""
Database Seeding Script
-----------------------
Pre-populates the database with global geographic macro-regions.
Designed to be idempotent (safe to run multiple times).
"""

from sqlalchemy.orm import Session
from geoalchemy2.elements import WKTElement
import src.models as models

# ==============================================================================
# ⚠️ IMPLEMENTATION WARNING for Auto-Zone Assignment (Issue #199)
# ==============================================================================
# Some macro-regions below overlap geographically (e.g., "Italy - North" sits 
# completely inside "Western Europe"). 
# 
# When implementing the ST_Contains spatial query for automatic sensor registration,
# you MUST order the matched zones by polygon area in ASCENDING order.
# 
# Example PostGIS logic: ORDER BY ST_Area(geom) ASC LIMIT 1
# This guarantees the sensor is assigned to the most specific (smallest) region.
# ==============================================================================

# Curated list of macro-regions. 
# WKT Polygon format: POLYGON((min_lon min_lat, max_lon min_lat, max_lon max_lat, min_lon max_lat, min_lon min_lat))
ZONES_DATA = [
    {"city": "Italy - North", "geom": "POLYGON((6.6 44.0, 13.8 44.0, 13.8 47.1, 6.6 47.1, 6.6 44.0))"},
    {"city": "Italy - Center", "geom": "POLYGON((9.7 41.2, 14.3 41.2, 14.3 44.0, 9.7 44.0, 9.7 41.2))"},
    {"city": "Italy - South & Islands", "geom": "POLYGON((8.0 35.0, 18.5 35.0, 18.5 41.2, 8.0 41.2, 8.0 35.0))"},
    {"city": "Western Europe", "geom": "POLYGON((-10.0 36.0, 20.0 36.0, 20.0 60.0, -10.0 60.0, -10.0 36.0))"},
    {"city": "North America", "geom": "POLYGON((-168.0 15.0, -50.0 15.0, -50.0 75.0, -168.0 75.0, -168.0 15.0))"},
    {"city": "South America", "geom": "POLYGON((-85.0 -55.0, -30.0 -55.0, -30.0 15.0, -85.0 15.0, -85.0 -55.0))"},
    {"city": "East Asia", "geom": "POLYGON((73.0 15.0, 150.0 15.0, 150.0 55.0, 73.0 55.0, 73.0 15.0))"},
    # The ultimate fallback region (No boundary constraints)
    {"city": "Unknown Region", "geom": None} 
]

def seed_zones(db: Session):
    print("🌱 Running database seeder for Zones...")
    
    for z_data in ZONES_DATA:
        existing_zone = db.query(models.Zone).filter(models.Zone.city == z_data["city"]).first()
        
        if not existing_zone:
            geom_elem = WKTElement(z_data["geom"], srid=4326) if z_data["geom"] else None
            new_zone = models.Zone(
                city=z_data["city"],
                geom=geom_elem
            )
            db.add(new_zone)
            print(f"   ➕ Created Zone: {z_data['city']}")
            
    db.commit()
    print("✅ Seeding complete.")