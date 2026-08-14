"""
Geographic zoning helpers (geohash-based Redis fast path)
---------------------------------------------------------
PostGIS remains the single source of truth for zone geometry. This module
pre-computes, at seed time, the set of geohash cells that intersect each zone
polygon and exposes a fast-path resolver backed by Redis SET lookups.

On a Redis miss (or an ambiguous multi-zone match) the caller falls back to
the authoritative PostGIS ``ST_Contains`` query, so correctness never depends
on the cache being warm.

The geohash encoder below implements the standard algorithm (as used by
PostGIS ``ST_GeoHash``) in pure Python, so the Redis keys written at seed time
match the keys computed at runtime with zero new dependencies.
"""

import math
import os

import redis
import src.models as models
from sqlalchemy import text
from sqlalchemy.orm import Session

# --- Configuration -----------------------------------------------------------
# Geohash precision used for the Redis zone-index lookup sets.
# prec 3 -> cell ~1.40625deg (~156 km at the equator): small cardinality, so
# the zone index set stays cheap to bulk-cover at seed time.
ZONE_INDEX_PRECISION = int(os.getenv("ZONE_INDEX_PRECISION", "3"))

# Geohash precision used for per-area event cooldown keys.
# prec 4 -> cell ~0.7deg (~39 x 19 km at the equator), aligned with the
# 50-100 km destructive surface-wave reach documented in the roadmap.
COOLDOWN_PRECISION = int(os.getenv("COOLDOWN_PRECISION", "4"))

ZONE_INDEX_KEY_PREFIX = "zoneindex"
COOLDOWN_KEY_PREFIX = "alert_cooldown"

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_sync = redis.from_url(REDIS_URL, decode_responses=True)

# --- Pure-Python geohash encoder (matches PostGIS ST_GeoHash) ---------------
_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def point_to_geohash(latitude: float, longitude: float, precision: int) -> str:
    """Encode a WGS84 coordinate into a geohash string of ``precision`` chars."""
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    bit = 0
    ch = 0
    even = True
    out = []
    while len(out) < precision:
        if even:
            mid = (lon_range[0] + lon_range[1]) / 2.0
            if longitude >= mid:
                ch |= 1 << 4 - bit
                lon_range[0] = mid
            else:
                lon_range[1] = mid
        else:
            mid = (lat_range[0] + lat_range[1]) / 2.0
            if latitude >= mid:
                ch |= 1 << 4 - bit
                lat_range[0] = mid
            else:
                lat_range[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            out.append(_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(out)


def _refine_axis(ranges: list[float], cd: int, mask: int) -> None:
    """Narrow ``ranges`` to the half-interval selected by one geohash bit."""
    mid = (ranges[0] + ranges[1]) / 2.0
    if cd & mask:
        ranges[0] = mid
    else:
        ranges[1] = mid


def geohash_bounds(geohash: str) -> tuple[float, float, float, float]:
    """Decode a geohash into ``(lon_min, lat_min, lon_max, lat_max)``."""
    lat_range = [-90.0, 90.0]
    lon_range = [-180.0, 180.0]
    even = True
    for char in geohash:
        cd = _BASE32.index(char)
        for mask in (16, 8, 4, 2, 1):
            if even:
                _refine_axis(lon_range, cd, mask)
            else:
                _refine_axis(lat_range, cd, mask)
            even = not even
    return lon_range[0], lat_range[0], lon_range[1], lat_range[1]


def _cell_indices_to_geohash(lon_index: int, lat_index: int, precision: int) -> str:
    """Reconstruct the geohash of a cell from its (lon, lat) grid indices."""
    bits = precision * 5
    lon_bits = (bits + 1) // 2
    lat_bits = bits // 2
    chars = []
    for c in range(precision):
        chunk = 0
        for k in range(5):
            bit_pos = c * 5 + k
            if bit_pos % 2 == 0:
                axis_bit = (lon_index >> (lon_bits - 1 - bit_pos // 2)) & 1
            else:
                axis_bit = (lat_index >> (lat_bits - 1 - bit_pos // 2)) & 1
            chunk = (chunk << 1) | axis_bit
        chars.append(_BASE32[chunk])
    return "".join(chars)


def _cells_in_bbox(lat_min: float, lon_min: float, lat_max: float, lon_max: float, precision: int) -> list[str]:
    """List the geohash cells (at ``precision``) whose rectangle overlaps the bbox."""
    bits = precision * 5
    lon_bits = (bits + 1) // 2
    lat_bits = bits // 2
    lon_step = 360.0 / (1 << lon_bits)
    lat_step = 180.0 / (1 << lat_bits)

    lon_start = max(0, math.floor((lon_min + 180.0) / lon_step))
    lon_end = min((1 << lon_bits) - 1, math.floor((lon_max + 180.0) / lon_step))
    lat_start = max(0, math.floor((lat_min + 90.0) / lat_step))
    lat_end = min((1 << lat_bits) - 1, math.floor((lat_max + 90.0) / lat_step))

    cells = []
    for lat_i in range(lat_start, lat_end + 1):
        for lon_i in range(lon_start, lon_end + 1):
            cells.append(_cell_indices_to_geohash(lon_i, lat_i, precision))
    return cells


def _zone_bbox(
    db: Session, zone_id: int
) -> tuple[float, float, float, float] | None:
    """Fetch ``(lon_min, lat_min, lon_max, lat_max)`` for a zone polygon."""
    row = db.execute(
        text("SELECT ST_XMin(geom), ST_YMin(geom), ST_XMax(geom), ST_YMax(geom) FROM zones WHERE id = :zid"),
        {"zid": zone_id},
    ).first()
    if not row or any(v is None for v in row):
        return None
    return tuple(float(v) for v in row)


def zone_covering_geohashes(db: Session, zone: models.Zone, precision: int = ZONE_INDEX_PRECISION) -> list[str]:
    """Return the geohash cells (at ``precision``) intersecting a zone polygon."""
    bbox = _zone_bbox(db, zone.id)
    if bbox is None:
        return []
    lon_min, lat_min, lon_max, lat_max = bbox
    candidates = _cells_in_bbox(lat_min, lon_min, lat_max, lon_max, precision)
    if not candidates:
        return []

    # Stroke each candidate cell's rectangle into a temp table, then keep only
    # the cells actually intersecting the zone polygon. Static SQL + bound
    # params throughout (no f-string interpolation), and no bind-param limits.
    # IF NOT EXISTS + DELETE keep the temp table reusable across zones within
    # the same transaction (ON COMMIT DROP fires only at commit).
    db.execute(text("CREATE TEMP TABLE IF NOT EXISTS _zone_cells(cell_key text, geom geometry) ON COMMIT DROP"))
    db.execute(text("DELETE FROM _zone_cells"))
    db.execute(
        text(
            "INSERT INTO _zone_cells (cell_key, geom) "
            "VALUES (:key, ST_GeomFromText(:wkt, 4326))"
        ),
        [
            {"key": cell, "wkt": _cell_wkt(cell)}
            for cell in candidates
        ],
    )

    rows = db.execute(
        text(
            "SELECT c.cell_key FROM _zone_cells c "
            "WHERE ST_Intersects(c.geom, (SELECT geom FROM zones WHERE id = :zid))"
        ),
        {"zid": zone.id},
    ).fetchall()
    return [row[0] for row in rows]


def _cell_wkt(cell: str) -> str:
    """WKT rectangle for a geohash cell (used only to feed ST_GeomFromText)."""
    lon_c, lat_c, lon_c2, lat_c2 = geohash_bounds(cell)
    return (
        f"POLYGON(({lon_c} {lat_c},{lon_c2} {lat_c},"
        f"{lon_c2} {lat_c2},{lon_c} {lat_c2},{lon_c} {lat_c}))"
    )


def clear_zone_index(redis_client=redis_sync) -> None:
    """Delete every zone-index key (idempotent rebuild helper)."""
    for key in redis_client.scan_iter(match=f"{ZONE_INDEX_KEY_PREFIX}:*"):
        redis_client.delete(key)


def build_zone_index(
    db: Session,
    redis_client=redis_sync,
    precision: int = ZONE_INDEX_PRECISION,
) -> dict[str, list[int]]:
    """
    (Re)build the Redis zone-index from the authoritative PostGIS polygons.

    Maps ``zoneindex:<geohash>`` -> SET of zone ids whose polygon intersects
    that cell. Cells with zero matches are simply absent from Redis.
    """
    clear_zone_index(redis_client)
    zones = db.query(models.Zone).filter(models.Zone.geom.isnot(None)).all()

    index: dict[str, list[int]] = {}
    for zone in zones:
        cells = zone_covering_geohashes(db, zone, precision)
        for cell in cells:
            index.setdefault(cell, []).append(zone.id)
        print(f"   🌐 Indexed Zone '{zone.city}': {len(cells)} cells", flush=True)

    pipe = redis_client.pipeline(transaction=False)
    for cell, zone_ids in index.items():
        pipe.sadd(f"{ZONE_INDEX_KEY_PREFIX}:{cell}", *zone_ids)
    pipe.execute()
    print(f"✅ Zone geo-index rebuilt: {len(index)} cells across {len(zones)} zones", flush=True)
    return index


def candidate_zone_ids(
    latitude: float,
    longitude: float,
    redis_client=redis_sync,
    precision: int = ZONE_INDEX_PRECISION,
) -> set[int]:
    """Best-effort Redis fast path: zone ids whose cells contain the coordinate."""
    try:
        cell = point_to_geohash(latitude, longitude, precision)
        members = redis_client.smembers(f"{ZONE_INDEX_KEY_PREFIX}:{cell}")
        return {int(m) for m in members}
    except Exception:
        return set()
