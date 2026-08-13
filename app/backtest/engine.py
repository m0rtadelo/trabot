import math
import uuid
from datetime import datetime

from app.backtest.models import (
    BacktestParams,
    BacktestResult,
    EquityPoint,
    TradeResult,
)
from app.backtest.metrics import compute_metrics
from app.market.models import BarData
from app.portfolio.models import OrderSide
from app.portfolio.simulator import Simulator
from app.strategy.features import compute_features
from app.strategy.models import SignalAction
from app.strategy.strategy import Strategy


class BacktestEngine:
    def __init__(
        self,
        strategy: Strategy,
        initial_capital: float,
        commission: float = 0.0,
        slippage_bps: int = 5,
        max_position_pct: float = 0.20,
        symbols: list[str] | None = None,
    ) -> None:
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.commission = commission
        self.slippage_bps = slippage_bps
        self.max_position_pct = max_position_pct
        self.symbols = symbols or []

    def run(self, bars_by_symbol: dict[str, list[BarData]]) -> BacktestResult:
        bars_by_symbol = {
            symbol: sorted(bars, key=lambda b: b.timestamp)
            for symbol, bars in bars_by_symbol.items()
            if bars
        }
        symbols = list(bars_by_symbol)

        features_by_symbol = {
            symbol: compute_features(bars) for symbol, bars in bars_by_symbol.items()
        }
        index_by_symbol = {
            symbol: {b.timestamp: i for i, b in enumerate(bars)}
            for symbol, bars in bars_by_symbol.items()
        }

        all_timestamps = sorted(
            {b.timestamp for bars in bars_by_symbol.values() for b in bars}
        )

        simulator = Simulator(
            initial_capital=self.initial_capital,
            commission=self.commission,
            slippage_bps=self.slippage_bps,
            max_position_pct=self.max_position_pct,
        )

        pending: dict[str, OrderSide] = {}
        last_prices: dict[str, float] = {}
        equity_curve: list[EquityPoint] = []

        for timestamp in all_timestamps:
            for symbol in list(pending):
                if timestamp not in index_by_symbol[symbol]:
                    continue
                bar = bars_by_symbol[symbol][index_by_symbol[symbol][timestamp]]
                side = pending.pop(symbol)
                if side == OrderSide.BUY:
                    simulator.buy(symbol, timestamp, bar.open)
                else:
                    simulator.sell(symbol, timestamp, bar.open)

            for symbol in symbols:
                if timestamp in index_by_symbol[symbol]:
                    bar = bars_by_symbol[symbol][index_by_symbol[symbol][timestamp]]
                    last_prices[symbol] = bar.close

            for symbol in symbols:
                if timestamp not in index_by_symbol[symbol]:
                    continue
                features = features_by_symbol[symbol][index_by_symbol[symbol][timestamp]]
                signal = self.strategy.evaluate(features)
                has_position = symbol in simulator.portfolio.positions
                if signal.action == SignalAction.BUY and not has_position:
                    pending[symbol] = OrderSide.BUY
                elif signal.action == SignalAction.SELL and has_position:
                    pending[symbol] = OrderSide.SELL
                else:
                    pending.pop(symbol, None)

            equity_curve.append(
                EquityPoint(
                    timestamp=timestamp,
                    value=simulator.portfolio.total_value(last_prices),
                )
            )

        trades = self._build_trades(simulator)
        metrics = compute_metrics(self.initial_capital, equity_curve, trades)
        bh_final, bh_return = buy_and_hold(bars_by_symbol, self.initial_capital)

        start = all_timestamps[0] if all_timestamps else datetime.now()
        end = all_timestamps[-1] if all_timestamps else start
        params = BacktestParams(
            strategy=self.strategy.__class__.__name__,
            symbols=self.symbols or symbols,
            start=start,
            end=end,
            initial_capital=self.initial_capital,
            commission=self.commission,
            slippage_bps=self.slippage_bps,
        )

        return BacktestResult(
            backtest_id=str(uuid.uuid4()),
            params=params,
            metrics=metrics,
            equity_curve=equity_curve,
            trades=trades,
            buy_and_hold_final=bh_final,
            buy_and_hold_return=bh_return,
        )

    @staticmethod
    def _build_trades(simulator: Simulator) -> list[TradeResult]:
        trades: list[TradeResult] = []
        entry_timestamp: dict[str, datetime] = {}
        for order in simulator.orders:
            if order.side == OrderSide.BUY:
                entry_timestamp[order.symbol] = order.timestamp
                continue
            if order.realized_pnl is None:
                continue
            quantity = order.quantity
            entry_price = order.exec_price - (
                order.realized_pnl + order.commission
            ) / quantity
            trades.append(
                TradeResult(
                    symbol=order.symbol,
                    entry_timestamp=entry_timestamp.get(
                        order.symbol, order.timestamp
                    ),
                    exit_timestamp=order.timestamp,
                    entry_price=entry_price,
                    exit_price=order.exec_price,
                    quantity=quantity,
                    pnl=order.realized_pnl,
                )
            )
        return trades


def buy_and_hold(
    bars_by_symbol: dict[str, list[BarData]],
    initial_capital: float,
) -> tuple[float, float]:
    symbols = [s for s, bars in bars_by_symbol.items() if bars]
    if not symbols:
        return initial_capital, 0.0

    budget = initial_capital / len(symbols)
    cash = initial_capital
    quantities: dict[str, float] = {}

    for symbol in symbols:
        entry = bars_by_symbol[symbol][0]
        quantity = math.floor(budget / entry.open)
        quantities[symbol] = quantity
        cash -= quantity * entry.open

    final = cash + sum(
        quantities[symbol] * bars_by_symbol[symbol][-1].close
        for symbol in symbols
    )
    return final, final / initial_capital - 1.0
