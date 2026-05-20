-- Connect to correct database (optional if executed in correct environment, but secure)
\c monitoraggio_db;

-- Turn PostGIS ON
CREATE EXTENSION IF NOT EXISTS postgis;