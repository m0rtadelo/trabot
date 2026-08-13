from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class EquityPoint:
    timestamp: datetime
    value: float


@dataclass(frozen=True)
class TradeResult:
    symbol: str
    entry_timestamp: datetime
    exit_timestamp: datetime
    entry_price: float
    exit_price: float
    quantity: float
    pnl: float


@dataclass(frozen=True)
class BacktestMetrics:
    initial_capital: float
    final_capital: float
    total_return: float
    annualized_return: float
    max_drawdown: float
    num_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_winning_trade: float
    avg_losing_trade: float
    profit_factor: Optional[float]
    sharpe_ratio: float

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BacktestParams:
    strategy: str
    symbols: list[str]
    start: datetime
    end: datetime
    initial_capital: float
    commission: float
    slippage_bps: int


@dataclass(frozen=True)
class BacktestResult:
    backtest_id: str
    params: BacktestParams
    metrics: BacktestMetrics
    equity_curve: list[EquityPoint]
    trades: list[TradeResult]
    buy_and_hold_final: float
    buy_and_hold_return: float
