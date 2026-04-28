# tests/test_time_provider.py
"""Tests unitaires — TimeProvider"""

import pytest
from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo
from core.neron_time.time_provider import TimeProvider, JOURS, MOIS


class TestTimeProvider:
    def test_default_timezone(self):
        tp = TimeProvider()
        assert str(tp.tz) == "Europe/Paris"

    def test_invalid_timezone_fallback(self):
        tp = TimeProvider(tz="Continent/FakeCity")
        assert str(tp.tz) == "Europe/Paris"

    def test_now_returns_localized_datetime(self):
        tp = TimeProvider()
        n = tp.now()
        assert n.tzinfo is not None

    def test_iso_format(self):
        tp = TimeProvider()
        iso = tp.iso()
        assert "T" in iso
        # Parsable
        datetime.fromisoformat(iso)

    def test_timestamp_is_float(self):
        tp = TimeProvider()
        assert isinstance(tp.timestamp(), float)

    def test_date_format(self):
        tp = TimeProvider()
        d = tp.date()
        parts = d.split("/")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_time_format(self):
        tp = TimeProvider()
        t = tp.time()
        parts = t.split(":")
        assert len(parts) == 3

    def test_human_contains_day_and_month(self):
        tp = TimeProvider()
        h = tp.human()
        assert any(j in h for j in JOURS)
        assert any(m in h for m in MOIS)

    def test_human_fixed_datetime(self):
        """Test déterministe avec un datetime fixé."""
        tp = TimeProvider(tz="Europe/Paris")
        # Lundi 7 avril 2025 à 09h05
        fixed = datetime(2025, 4, 7, 9, 5, 0, tzinfo=ZoneInfo("Europe/Paris"))
        with patch.object(tp, "now", return_value=fixed):
            h = tp.human()
        assert "lundi" in h
        assert "avril" in h
        assert "09h05" in h
        assert "2025" in h

    @pytest.mark.parametrize("month_idx,expected", [
        (1, "janvier"), (6, "juin"), (12, "décembre"),
    ])
    def test_mois_mapping(self, month_idx, expected):
        assert MOIS[month_idx - 1] == expected

    @pytest.mark.parametrize("day_idx,expected", [
        (0, "lundi"), (4, "vendredi"), (6, "dimanche"),
    ])
    def test_jours_mapping(self, day_idx, expected):
        assert JOURS[day_idx] == expected
