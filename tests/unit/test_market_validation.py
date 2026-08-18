from datetime import datetime, timedelta, timezone

import pytest

from app.market.models import BarData
from app.market.validation import BarValidationError, validate_bars


def make_bar(offset_hours: int = 0, **kwargs) -> BarData:
    defaults = {
        "symbol": "AAPL",
        "timestamp": datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)
        + timedelta(hours=offset_hours),
        "open": 100.0,
        "high": 105.0,
        "low": 99.0,
        "close": 103.0,
        "volume": 1000,
    }
    defaults.update(kwargs)
    return BarData(**defaults)


def test_valid_bars_pass() -> None:
    bars = [make_bar(0), make_bar(1), make_bar(2)]
    validate_bars(bars)


def test_naive_timestamp_rejected() -> None:
    with pytest.raises(BarValidationError, match="timezone-aware"):
        validate_bars([make_bar(timestamp=datetime(2024, 1, 2, 15, 0))])


def test_non_utc_timestamp_rejected() -> None:
    ts = datetime(2024, 1, 2, 10, 0, tzinfo=timezone(timedelta(hours=-5)))
    with pytest.raises(BarValidationError, match="UTC"):
        validate_bars([make_bar(timestamp=ts)])


def test_negative_price_rejected() -> None:
    with pytest.raises(BarValidationError, match="positive"):
        validate_bars([make_bar(close=-1.0)])


def test_high_below_close_rejected() -> None:
    with pytest.raises(BarValidationError, match="high below"):
        validate_bars([make_bar(high=90.0, close=103.0)])


def test_low_above_open_rejected() -> None:
    with pytest.raises(BarValidationError, match="low above"):
        validate_bars([make_bar(low=110.0, open=100.0)])


def test_negative_volume_rejected() -> None:
    with pytest.raises(BarValidationError, match="negative volume"):
        validate_bars([make_bar(volume=-5)])


def test_unsorted_bars_rejected() -> None:
    with pytest.raises(BarValidationError, match="time-ordered"):
        validate_bars([make_bar(2), make_bar(0)])


def test_same_timestamp_different_symbols_allowed() -> None:
    bars = [
        make_bar(0, symbol="AAPL"),
        make_bar(0, symbol="MSFT"),
        make_bar(1, symbol="AAPL"),
        make_bar(1, symbol="MSFT"),
    ]
    validate_bars(bars)


def test_same_timestamp_same_symbol_rejected() -> None:
    with pytest.raises(BarValidationError, match="time-ordered"):
        validate_bars([make_bar(0, symbol="AAPL"), make_bar(0, symbol="AAPL")])
