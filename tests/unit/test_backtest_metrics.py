from datetime import datetime, timedelta, timezone

import pytest

from app.backtest.metrics import (
    annualized_return,
    compute_metrics,
    max_drawdown,
    sharpe_ratio,
    total_return,
)
from app.backtest.models import EquityPoint, TradeResult

BASE = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)


def test_total_return() -> None:
    assert total_return(1000.0, 1200.0) == pytest.approx(0.2)
    assert total_return(0.0, 100.0) == 0.0


def test_annualized_return_one_year() -> None:
    start = BASE
    end = BASE + timedelta(days=365.25)
    assert annualized_return(1000.0, 2000.0, start, end) == pytest.approx(1.0)


def test_annualized_return_no_elapsed_time() -> None:
    assert annualized_return(1000.0, 1100.0, BASE, BASE) == 0.0


def test_max_drawdown() -> None:
    values = [1000.0, 1100.0, 900.0, 1050.0, 1300.0, 1200.0]
    assert max_drawdown(values) == pytest.approx((1100.0 - 900.0) / 1100.0)


def test_max_drawdown_never_negative() -> None:
    assert max_drawdown([100.0, 200.0, 300.0]) == 0.0


def test_sharpe_ratio_flat_is_zero() -> None:
    equity = [EquityPoint(BASE + timedelta(days=i), 100.0) for i in range(5)]
    assert sharpe_ratio(equity) == 0.0


def test_sharpe_ratio_positive_for_rising_series() -> None:
    equity = [
        EquityPoint(BASE + timedelta(days=i), 100.0 * (1.05**i))
        for i in range(30)
    ]
    assert sharpe_ratio(equity) > 0.0


def test_sharpe_ratio_short_series_is_zero() -> None:
    assert sharpe_ratio([EquityPoint(BASE, 100.0)]) == 0.0


def test_compute_metrics_known_values() -> None:
    equity = [
        EquityPoint(BASE + timedelta(days=i), v)
        for i, v in enumerate([1000.0, 1100.0, 900.0, 1200.0])
    ]
    trades = [
        TradeResult("AAPL", BASE, BASE, 100, 200, 1, 100.0),
        TradeResult("AAPL", BASE, BASE, 100, 300, 1, 200.0),
        TradeResult("AAPL", BASE, BASE, 100, 50, 1, -50.0),
    ]
    metrics = compute_metrics(1000.0, equity, trades)

    assert metrics.final_capital == pytest.approx(1200.0)
    assert metrics.total_return == pytest.approx(0.2)
    assert metrics.num_trades == 3
    assert metrics.winning_trades == 2
    assert metrics.losing_trades == 1
    assert metrics.win_rate == pytest.approx(2 / 3)
    assert metrics.avg_winning_trade == pytest.approx(150.0)
    assert metrics.avg_losing_trade == pytest.approx(50.0)
    assert metrics.profit_factor == pytest.approx(6.0)
    assert metrics.max_drawdown == pytest.approx((1100.0 - 900.0) / 1100.0)


def test_compute_metrics_no_trades() -> None:
    equity = [EquityPoint(BASE + timedelta(days=i), 1000.0) for i in range(5)]
    metrics = compute_metrics(1000.0, equity, [])
    assert metrics.num_trades == 0
    assert metrics.win_rate == 0.0
    assert metrics.profit_factor is None
