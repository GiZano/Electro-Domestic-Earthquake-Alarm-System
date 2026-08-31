import pytest
from datetime import datetime, timezone
from src.triangulation import triangulate_epicenter, haversine_distance

def test_haversine_distance():
    # Test Rome to Milan distance (roughly 477 km)
    lat1, lon1 = 41.9028, 12.4964
    lat2, lon2 = 45.4642, 9.1900
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    assert 470 < dist < 485  # Validate within reasonable approximation bounds

def test_triangulate_epicenter_insufficient_data():
    triggers = [{"latitude": 41.9, "longitude": 12.5, "timestamp": 1720000000.0, "magnitude": 4.5}]
    with pytest.raises(ValueError, match="Need at least 3 triggers for triangulation"):
        triangulate_epicenter(triggers)

def test_triangulate_epicenter_weighted_centroid():
    triggers = [
        {"latitude": 10.0, "longitude": 10.0, "timestamp": 1720000000.0, "magnitude": 2.0},
        {"latitude": 20.0, "longitude": 10.0, "timestamp": 1720000002.0, "magnitude": 2.0},
        {"latitude": 10.0, "longitude": 20.0, "timestamp": 1720000003.0, "magnitude": 2.0}
    ]
    # Since all magnitudes are equal (weight 2.0), the centroid should be the arithmetic mean
    # lat: (10 + 20 + 10) / 3 = 13.333...
    # lon: (10 + 10 + 20) / 3 = 13.333...
    result = triangulate_epicenter(triggers)
    assert pytest.approx(result["latitude"], 0.001) == 13.333
    assert pytest.approx(result["longitude"], 0.001) == 13.333

def test_triangulate_epicenter_magnitude_bias():
    triggers = [
        {"latitude": 10.0, "longitude": 10.0, "timestamp": 1720000000.0, "magnitude": 10.0}, # Huge weight
        {"latitude": 20.0, "longitude": 10.0, "timestamp": 1720000002.0, "magnitude": 1.0},
        {"latitude": 10.0, "longitude": 20.0, "timestamp": 1720000003.0, "magnitude": 1.0}
    ]
    # Centroid should be heavily biased towards (10, 10)
    result = triangulate_epicenter(triggers)
    assert result["latitude"] < 12.0
    assert result["longitude"] < 12.0

def test_triangulate_epicenter_origin_time():
    # Simulate a trigger exactly 60km away from epicenter
    # V_P = 6.0 km/s -> travel time should be 10 seconds.
    # We place a heavy node at (0, 0) to force the epicenter there.
    triggers = [
        {"latitude": 0.0, "longitude": 0.0, "timestamp": 1720000010.0, "magnitude": 1000.0}, 
        {"latitude": 0.0, "longitude": 0.1, "timestamp": 1720000012.0, "magnitude": 0.1},
        {"latitude": 0.1, "longitude": 0.0, "timestamp": 1720000013.0, "magnitude": 0.1}
    ]
    result = triangulate_epicenter(triggers)
    # The first trigger is 1720000010.0. 
    # Its distance to the centroid (0,0) is basically 0 km -> travel time 0.
    # Origin time should be exactly 1720000010.0
    
    dt = datetime.fromisoformat(result["origin_time"])
    assert dt.timestamp() == 1720000010.0

def test_triangulate_epicenter_isoformat_parsing():
    triggers = [
        {"latitude": 10.0, "longitude": 10.0, "timestamp": "2024-07-03T12:26:40Z", "magnitude": 2.0},
        {"latitude": 20.0, "longitude": 10.0, "timestamp": "2024-07-03T12:26:42Z", "magnitude": 2.0},
        {"latitude": 10.0, "longitude": 20.0, "timestamp": "2024-07-03T12:26:43Z", "magnitude": 2.0}
    ]
    result = triangulate_epicenter(triggers)
    assert "T" in result["origin_time"]
    assert "+00:00" in result["origin_time"] or "Z" in result["origin_time"]
