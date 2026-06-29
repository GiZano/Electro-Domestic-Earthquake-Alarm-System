import pytest
from src.worker import estimate_magnitude


class TestEstimateMagnitude:
    def test_zero_value(self):
        assert estimate_magnitude(0) == 0.0

    def test_negative_value(self):
        assert estimate_magnitude(-100) == 0.0

    def test_small_value(self):
        mag = estimate_magnitude(100)
        assert 0.0 <= mag <= 3.0

    def test_moderate_quake(self):
        mag = estimate_magnitude(3000)
        assert 3.0 <= mag <= 5.0

    def test_large_value_clamped(self):
        mag = estimate_magnitude(1000000)
        assert mag <= 9.9
        assert mag > 5.0

    def test_known_value(self):
        mag = estimate_magnitude(126)
        expected = 2.9
        assert abs(mag - expected) <= 0.2

    def test_trigger_threshold(self):
        mag = estimate_magnitude(5500)
        assert mag >= 4.5

    def test_below_threshold(self):
        mag = estimate_magnitude(200)
        assert mag < 4.5

    def test_consistency(self):
        assert estimate_magnitude(1000) == estimate_magnitude(1000)

    def test_rounding(self):
        mag = estimate_magnitude(555)
        assert isinstance(mag, float)
