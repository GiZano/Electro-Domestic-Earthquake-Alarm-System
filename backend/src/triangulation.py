import math
from datetime import datetime, timezone

# Average P-wave velocity in crust ~ 6.0 km/s
V_P = 6.0

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def triangulate_epicenter(triggers: list[dict]) -> dict:
    """
    Computes the estimated epicenter and origin time from a cluster of sensor triggers.
    
    triggers: list of dicts with 'latitude', 'longitude', 'timestamp', 'magnitude'
    Returns dict with 'latitude', 'longitude', 'origin_time' (ISO 8601 string).
    
    NOTE (v2.0 MVP): Uses a magnitude-weighted spatial centroid as an approximation 
    of the epicenter. Full TDOA (Time Difference of Arrival) non-linear least squares 
    can be swapped in later for precise calculation.
    """
    if len(triggers) < 3:
        raise ValueError("Need at least 3 triggers for triangulation")
    
    sum_lat = 0.0
    sum_lon = 0.0
    sum_weight = 0.0
    
    for t in triggers:
        weight = t.get('magnitude', 1.0)
        sum_lat += t['latitude'] * weight
        sum_lon += t['longitude'] * weight
        sum_weight += weight
        
    epi_lat = sum_lat / sum_weight
    epi_lon = sum_lon / sum_weight
    
    # Estimate origin time using the closest sensor's arrival time
    def get_ts(t):
        ts = t['timestamp']
        if isinstance(ts, str):
            # Parse ISO string
            return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
        return ts

    first_trigger = min(triggers, key=get_ts)
    dist_km = haversine_distance(epi_lat, epi_lon, first_trigger['latitude'], first_trigger['longitude'])
    travel_time_s = dist_km / V_P
    
    origin_ts = get_ts(first_trigger) - travel_time_s
    origin_time = datetime.fromtimestamp(origin_ts, tz=timezone.utc)
    
    return {
        "latitude": epi_lat,
        "longitude": epi_lon,
        "origin_time": origin_time.isoformat()
    }
