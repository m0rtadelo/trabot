from datetime import datetime, timezone

import pytest

from app.portfolio.models import OrderSide
from app.portfolio.risk import PositionSizer
from app.portfolio.simulator import Simulator

TS = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)


@pytest.fixture()
def sim() -> Simulator:
    return Simulator(initial_capital=1000.0, commission=0.0, slippage_bps=0)


def test_first_buy_uses_max_position_size(sim) -> None:
    order = sim.buy("AAPL", TS, 100.0)
    assert order is not None
    assert order.quantity == 2
    assert order.exec_price == 100.0
    assert sim.portfolio.cash == 800.0
    assert sim.portfolio.positions["AAPL"].avg_entry_price == 100.0


def test_no_rebuy_when_at_target_size(sim) -> None:
    sim.buy("AAPL", TS, 100.0)
    order = sim.buy("AAPL", TS, 100.0)
    assert order is None
    assert sim.portfolio.positions["AAPL"].quantity == 2


def test_buy_with_commission(sim) -> None:
    sim.commission = 0.5
    order = sim.buy("AAPL", TS, 100.0)
    assert order is not None
    assert order.quantity == 1
    assert order.commission == 0.5
    assert sim.portfolio.cash == 899.5


def test_buy_with_slippage() -> None:
    sim = Simulator(1000.0, commission=0.0, slippage_bps=100)
    order = sim.buy("AAPL", TS, 100.0)
    assert order is not None
    assert order.exec_price == 101.0
    assert order.quantity == 1


def test_buy_insufficient_cash_returns_none() -> None:
    sim = Simulator(100.0, commission=0.0, slippage_bps=0)
    assert sim.buy("AAPL", TS, 100.0) is None
    assert sim.portfolio.cash == 100.0


def test_cash_never_negative(sim) -> None:
    for _ in range(10):
        sim.buy("AAPL", TS, 100.0)
    assert sim.portfolio.cash >= 0.0


def test_sell_without_position_returns_none(sim) -> None:
    assert sim.sell("AAPL", TS, 100.0) is None


def test_sell_full_position(sim) -> None:
    sim.buy("AAPL", TS, 100.0)
    order = sim.sell("AAPL", TS, 110.0)
    assert order is not None
    assert order.realized_pnl == pytest.approx(20.0)
    assert sim.portfolio.cash == pytest.approx(1020.0)
    assert "AAPL" not in sim.portfolio.positions
    assert sim.realized_pnl == pytest.approx(20.0)


def test_sell_partial_position(sim) -> None:
    sim.buy("AAPL", TS, 100.0)
    order = sim.sell("AAPL", TS, 110.0, quantity=1)
    assert order is not None
    assert order.realized_pnl == pytest.approx(10.0)
    assert sim.portfolio.positions["AAPL"].quantity == 1
    assert sim.portfolio.cash == pytest.approx(910.0)


def test_sell_with_slippage() -> None:
    sim = Simulator(1000.0, commission=0.0, slippage_bps=100)
    sim.buy("AAPL", TS, 100.0)
    order = sim.sell("AAPL", TS, 110.0)
    assert order is not None
    assert order.quantity == 1
    assert order.exec_price == pytest.approx(108.9)
    assert order.realized_pnl == pytest.approx(7.9)


def test_sell_with_commission() -> None:
    sim = Simulator(1000.0, commission=5.0, slippage_bps=0)
    sim.buy("AAPL", TS, 100.0)
    order = sim.sell("AAPL", TS, 110.0)
    assert order is not None
    assert order.realized_pnl == pytest.approx(5.0)
    assert sim.portfolio.cash == pytest.approx(1000.0)


def test_weighted_average_entry_price() -> None:
    sim = Simulator(1000.0, commission=0.0, slippage_bps=0, max_position_pct=0.5)
    sim.buy("AAPL", TS, 100.0)
    sim.sell("AAPL", TS, 100.0, quantity=2)
    sim.buy("AAPL", TS, 120.0)
    position = sim.portfolio.positions["AAPL"]
    assert position.quantity == 4
    assert position.avg_entry_price == pytest.approx(105.0)
    assert sim.portfolio.cash == pytest.approx(580.0)


def test_unrealized_and_total_value(sim) -> None:
    sim.buy("AAPL", TS, 100.0)
    prices = {"AAPL": 110.0}
    assert sim.portfolio.market_value(prices) == pytest.approx(220.0)
    assert sim.portfolio.unrealized_pnl(prices) == pytest.approx(20.0)
    assert sim.portfolio.total_value(prices) == pytest.approx(1020.0)


def test_realized_pnl_accumulates() -> None:
    sim = Simulator(5000.0, commission=0.0, slippage_bps=0, max_position_pct=0.5)
    sim.buy("AAPL", TS, 100.0)
    sim.sell("AAPL", TS, 110.0)
    sim.buy("MSFT", TS, 50.0)
    sim.sell("MSFT", TS, 60.0)
    assert sim.realized_pnl == pytest.approx(770.0)


def test_multiple_positions(sim) -> None:
    sim.buy("AAPL", TS, 100.0)
    sim.buy("MSFT", TS, 50.0)
    assert set(sim.portfolio.positions) == {"AAPL", "MSFT"}


def test_orders_logged(sim) -> None:
    sim.buy("AAPL", TS, 100.0)
    sim.sell("AAPL", TS, 110.0)
    assert len(sim.orders) == 2
    assert sim.orders[0].side == OrderSide.BUY
    assert sim.orders[1].side == OrderSide.SELL
    assert sim.orders[0].timestamp == TS


def test_invalid_sizer_arguments() -> None:
    with pytest.raises(ValueError):
        PositionSizer(max_position_pct=0.0)
    with pytest.raises(ValueError):
        PositionSizer(max_position_pct=1.5)
