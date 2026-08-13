from datetime import datetime, timezone

import pytest

from app.strategy.models import CandleFeatures, SignalAction
from app.strategy.strategy import SmaRsiStrategy


def make_features(**overrides) -> CandleFeatures:
    defaults = {
        "symbol": "AAPL",
        "timestamp": datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
        "close": 100.0,
        "volume": 10_000,
        "sma20": 99.0,
        "sma50": 98.0,
        "sma200": 95.0,
        "rsi14": 60.0,
        "atr14": 2.0,
        "volume_sma20": 9_000,
    }
    defaults.update(overrides)
    return CandleFeatures(**defaults)


@pytest.fixture()
def strategy() -> SmaRsiStrategy:
    return SmaRsiStrategy()


def test_buy_when_all_conditions_met(strategy) -> None:
    signal = strategy.evaluate(make_features())
    assert signal.action == SignalAction.BUY
    assert signal.score == 1.0
    assert "SMA20 above SMA50" in signal.reason
    assert "Volume above average" in signal.reason


def test_buy_score_reflects_partial_conditions(strategy) -> None:
    features = make_features(volume=5_000)
    signal = strategy.evaluate(features)
    assert signal.action == SignalAction.HOLD
    assert signal.score == 0.0


def test_sell_when_sma20_below_sma50(strategy) -> None:
    features = make_features(sma20=97.0, sma50=98.0)
    signal = strategy.evaluate(features)
    assert signal.action == SignalAction.SELL
    assert "SMA20 below SMA50" in signal.reason


def test_sell_when_rsi_below_40(strategy) -> None:
    features = make_features(rsi14=35.0)
    signal = strategy.evaluate(features)
    assert signal.action == SignalAction.SELL
    assert "RSI below 40" in signal.reason


def test_hold_when_no_condition_met(strategy) -> None:
    features = make_features(rsi14=45.0)
    signal = strategy.evaluate(features)
    assert signal.action == SignalAction.HOLD
    assert signal.score == 0.0


def test_hold_when_insufficient_data(strategy) -> None:
    features = make_features(sma50=None)
    signal = strategy.evaluate(features)
    assert signal.action == SignalAction.HOLD
    assert signal.reason == ["Insufficient data to evaluate"]


def test_signal_fields_preserved(strategy) -> None:
    features = make_features()
    signal = strategy.evaluate(features)
    assert signal.symbol == "AAPL"
    assert signal.timestamp == features.timestamp
