from datetime import datetime, timedelta, timezone

import pytest

from app.backtest.engine import BacktestEngine, buy_and_hold
from app.market.models import BarData
from app.strategy.models import CandleFeatures, Signal, SignalAction
from app.strategy.strategy import SmaRsiStrategy, Strategy

BASE = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)


def make_bar(symbol: str, hour: int, open_: float, close: float) -> BarData:
    return BarData(
        symbol=symbol,
        timestamp=BASE + timedelta(hours=hour),
        open=open_,
        high=max(open_, close),
        low=min(open_, close),
        close=close,
        volume=10_000,
    )


class ScriptedStrategy(Strategy):
    def __init__(self, actions: list[SignalAction]) -> None:
        self.actions = list(actions)

    def evaluate(self, features: CandleFeatures) -> Signal:
        action = (
            self.actions.pop(0) if self.actions else SignalAction.HOLD
        )
        return Signal(features.symbol, features.timestamp, action, 1.0, ["scripted"])


def make_engine(strategy: Strategy) -> BacktestEngine:
    return BacktestEngine(
        strategy=strategy,
        initial_capital=1000.0,
        commission=0.0,
        slippage_bps=0,
        symbols=["AAPL"],
    )


def test_buy_executes_at_next_candle_open() -> None:
    bars = {
        "AAPL": [
            make_bar("AAPL", 0, 10.0, 10.0),
            make_bar("AAPL", 1, 11.0, 11.0),
            make_bar("AAPL", 2, 12.0, 12.0),
            make_bar("AAPL", 3, 13.0, 13.0),
        ]
    }
    engine = make_engine(
        ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL, SignalAction.HOLD])
    )
    result = engine.run(bars)

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.entry_timestamp == BASE + timedelta(hours=1)
    assert trade.entry_price == 11.0
    assert trade.exit_timestamp == BASE + timedelta(hours=3)
    assert trade.exit_price == 13.0
    assert trade.quantity == 18
    assert trade.pnl == pytest.approx(36.0)
    assert result.metrics.final_capital == pytest.approx(1036.0)
    assert result.metrics.num_trades == 1
    assert result.metrics.win_rate == 1.0
    assert result.metrics.profit_factor is None


def test_equity_curve_has_one_point_per_timestamp() -> None:
    bars = {
        "AAPL": [
            make_bar("AAPL", 0, 10.0, 10.0),
            make_bar("AAPL", 1, 11.0, 11.0),
            make_bar("AAPL", 2, 12.0, 12.0),
        ]
    }
    engine = make_engine(ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.HOLD]))
    result = engine.run(bars)
    assert len(result.equity_curve) == 3
    assert result.equity_curve[0].value == 1000.0


def test_sell_executes_next_open_after_signal() -> None:
    bars = {
        "AAPL": [
            make_bar("AAPL", 0, 10.0, 10.0),
            make_bar("AAPL", 1, 11.0, 11.0),
            make_bar("AAPL", 2, 20.0, 20.0),
            make_bar("AAPL", 3, 15.0, 15.0),
        ]
    }
    engine = make_engine(
        ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.SELL, SignalAction.HOLD])
    )
    result = engine.run(bars)

    trade = result.trades[0]
    assert trade.exit_timestamp == BASE + timedelta(hours=3)
    assert trade.exit_price == 15.0
    assert trade.pnl == pytest.approx((15.0 - 11.0) * 18)


def test_open_position_marked_to_market_at_close() -> None:
    bars = {
        "AAPL": [
            make_bar("AAPL", 0, 10.0, 10.0),
            make_bar("AAPL", 1, 11.0, 11.0),
            make_bar("AAPL", 2, 12.0, 14.0),
        ]
    }
    engine = make_engine(ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.HOLD]))
    result = engine.run(bars)
    last = result.equity_curve[-1]
    assert last.value == pytest.approx(802.0 + 18 * 14.0)


def test_buy_and_hold_baseline() -> None:
    bars = {
        "AAPL": [
            make_bar("AAPL", 0, 10.0, 10.0),
            make_bar("AAPL", 1, 11.0, 11.0),
            make_bar("AAPL", 2, 12.0, 12.0),
            make_bar("AAPL", 3, 13.0, 13.0),
        ]
    }
    final, ret = buy_and_hold(bars, 1000.0)
    assert final == pytest.approx(1300.0)
    assert ret == pytest.approx(0.3)


def test_buy_and_hold_multiple_symbols() -> None:
    bars = {
        "AAPL": [make_bar("AAPL", i, 10.0, 12.0) for i in range(3)],
        "MSFT": [make_bar("MSFT", i, 20.0, 30.0) for i in range(3)],
    }
    final, ret = buy_and_hold(bars, 1000.0)
    assert final == pytest.approx(50 * 12.0 + 25 * 30.0)
    assert ret == pytest.approx(final / 1000.0 - 1.0)


def test_real_strategy_smoke_test() -> None:
    import math

    symbols = ["AAPL"]
    bars_by_symbol: dict[str, list[BarData]] = {}
    for symbol in symbols:
        bars = []
        for i in range(300):
            close = 100.0 + 0.4 * i + 4.0 * math.sin(i * 0.3)
            volume = 10_000 + int(4_000 * math.sin(i * 0.7) + i * 50)
            bars.append(
                BarData(
                    symbol=symbol,
                    timestamp=BASE + timedelta(hours=i),
                    open=close,
                    high=close,
                    low=close,
                    close=close,
                    volume=max(10, volume),
                )
            )
        bars_by_symbol[symbol] = bars

    engine = BacktestEngine(
        strategy=SmaRsiStrategy(),
        initial_capital=1000.0,
        symbols=symbols,
    )
    result = engine.run(bars_by_symbol)
    assert len(result.equity_curve) == 300
    assert result.metrics.final_capital > 0
    assert result.metrics.final_capital != pytest.approx(1000.0)
    assert result.params.symbols == symbols


def test_engine_sorts_unsorted_input() -> None:
    bars = {
        "AAPL": [
            make_bar("AAPL", 2, 12.0, 12.0),
            make_bar("AAPL", 0, 10.0, 10.0),
            make_bar("AAPL", 1, 11.0, 11.0),
        ]
    }
    engine = make_engine(ScriptedStrategy([SignalAction.BUY, SignalAction.HOLD, SignalAction.HOLD]))
    result = engine.run(bars)
    assert result.equity_curve[0].timestamp == BASE
    assert result.equity_curve[-1].timestamp == BASE + timedelta(hours=2)
