# tests/test_time_provider.py
import pytest
from datetime import datetime
from neron_time.time_provider import TimeProvider


@pytest.fixture
def tp():
    return TimeProvider()


@pytest.fixture
def tp_utc():
    return TimeProvider(tz="UTC")


def test_now_returns_datetime(tp):
    assert isinstance(tp.now(), datetime)


def test_now_is_timezone_aware(tp):
    assert tp.now().tzinfo is not None


def test_now_timezone_paris(tp):
    assert "Europe/Paris" in str(tp.now().tzinfo)


def test_custom_timezone_utc(tp_utc):
    assert "UTC" in str(tp_utc.now().tzinfo)


def test_iso_returns_string(tp):
    assert isinstance(tp.iso(), str)


def test_iso_format_valid(tp):
    assert datetime.fromisoformat(tp.iso()) is not None


def test_human_returns_string(tp):
    assert isinstance(tp.human(), str)


def test_human_contains_h(tp):
    assert "h" in tp.human()


def test_timestamp_returns_float(tp):
    assert isinstance(tp.timestamp(), float)


def test_timestamp_positive(tp):
    assert tp.timestamp() > 0


def test_date_returns_string(tp):
    assert isinstance(tp.date(), str)


def test_date_format(tp):
    parts = tp.date().split("/")
    assert len(parts) == 3
    assert len(parts[2]) == 4


def test_time_returns_string(tp):
    assert isinstance(tp.time(), str)


def test_time_format(tp):
    assert len(tp.time().split(":")) == 3


def test_timestamps_coherent(tp):
    assert tp.timestamp() <= tp.timestamp()
