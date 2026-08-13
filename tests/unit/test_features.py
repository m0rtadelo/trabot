from datetime import datetime, timedelta, timezone

from app.market.models import BarData
from app.strategy.features import compute_features


def make_bars(count: int = 210) -> list[BarData]:
    base = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)
    return [
        BarData(
            symbol="AAPL",
            timestamp=base + timedelta(hours=i),
            open=100.0 + i,
            high=102.0 + i,
            low=99.0 + i,
            close=101.0 + i,
            volume=10_000 + i,
        )
        for i in range(count)
    ]


def test_returns_one_feature_per_bar() -> None:
    bars = make_bars(210)
    features = compute_features(bars)
    assert len(features) == 210
    assert features[0].timestamp == bars[0].timestamp


def test_warmup_none_then_values() -> None:
    features = compute_features(make_bars(210))
    assert features[0].sma20 is None
    assert features[0].sma50 is None
    assert features[0].sma200 is None
    assert features[0].rsi14 is None
    assert features[0].atr14 is None

    last = features[-1]
    assert last.sma20 is not None
    assert last.sma50 is not None
    assert last.sma200 is not None
    assert last.rsi14 is not None
    assert last.atr14 is not None
    assert last.volume_sma20 is not None


def test_sma20_is_running_mean_of_closes() -> None:
    features = compute_features(make_bars(210))
    last = features[-1]
    closes = [101.0 + i for i in range(210)]
    expected = sum(closes[-20:]) / 20
    assert last.sma20 == expected


def test_volume_above_average_detection() -> None:
    bars = make_bars(210)
    bars[-1] = BarData(
        symbol="AAPL",
        timestamp=bars[-1].timestamp,
        open=300.0,
        high=302.0,
        low=299.0,
        close=301.0,
        volume=1_000_000,
    )
    features = compute_features(bars)
    assert features[-1].volume > features[-1].volume_sma20
