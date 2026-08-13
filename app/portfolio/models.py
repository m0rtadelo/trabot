from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


@dataclass
class Position:
    symbol: str
    quantity: float
    avg_entry_price: float


@dataclass
class Portfolio:
    cash: float
    positions: dict[str, Position] = field(default_factory=dict)

    def cost_basis(self) -> float:
        return sum(p.quantity * p.avg_entry_price for p in self.positions.values())

    def market_value(self, prices: dict[str, float]) -> float:
        return sum(
            p.quantity * prices.get(p.symbol, p.avg_entry_price)
            for p in self.positions.values()
        )

    def total_value(self, prices: dict[str, float]) -> float:
        return self.cash + self.market_value(prices)

    def unrealized_pnl(self, prices: dict[str, float]) -> float:
        return sum(
            p.quantity * (prices.get(p.symbol, p.avg_entry_price) - p.avg_entry_price)
            for p in self.positions.values()
        )


@dataclass(frozen=True)
class Order:
    symbol: str
    timestamp: datetime
    side: OrderSide
    quantity: float
    exec_price: float
    commission: float
    realized_pnl: float | None = None
