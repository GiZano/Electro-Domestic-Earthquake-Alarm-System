# TimescaleDB + PostGIS in a single Postgres 15 image.
# The Timescale HA image bundles BOTH the timescaledb extension (hypertable /
# continuous-aggregate time-series substrate) and postgis (zone geometry), so
# geospatial and time-series data share one database, one image, one backup.
FROM timescale/timescaledb-ha:pg15

# shared_preload_libraries=timescaledb is already injected by this image's
# entrypoint; docker-compose additionally passes it via `command` to be explicit.

# The base image already runs as the non-root `postgres` user (uid 1000);
# declare it explicitly so the image never falls back to root.
USER postgres
