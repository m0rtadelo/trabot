import math
from datetime import datetime

from app.portfolio.models import Order, OrderSide, Portfolio, Position
from app.portfolio.risk import PositionSizer


class Simulator:
    def __init__(
        self,
        initial_capital: float,
        commission: float = 0.0,
        slippage_bps: int = 5,
        max_position_pct: float = 0.20,
    ) -> None:
        self.portfolio = Portfolio(cash=initial_capital)
        self.commission = commission
        self.slippage = slippage_bps / 10_000.0
        self.sizer = PositionSizer(max_position_pct)
        self.orders: list[Order] = []
        self._realized_pnl = 0.0

    @property
    def realized_pnl(self) -> float:
        return self._realized_pnl

    def buy(self, symbol: str, timestamp: datetime, price: float) -> Order | None:
        budget = self.sizer.buy_budget(self.portfolio, symbol)
        if budget <= self.commission:
            return None

        exec_price = price * (1.0 + self.slippage)
        quantity = math.floor((budget - self.commission) / exec_price)
        cost = quantity * exec_price + self.commission
        if quantity <= 0 or cost > self.portfolio.cash:
            return None

        self.portfolio.cash -= cost
        position = self.portfolio.positions.get(symbol)
        if position is None:
            self.portfolio.positions[symbol] = Position(symbol, quantity, exec_price)
        else:
            total_quantity = position.quantity + quantity
            position.avg_entry_price = (
                position.avg_entry_price * position.quantity + quantity * exec_price
            ) / total_quantity
            position.quantity = total_quantity

        order = Order(
            symbol=symbol,
            timestamp=timestamp,
            side=OrderSide.BUY,
            quantity=quantity,
            exec_price=exec_price,
            commission=self.commission,
        )
        self.orders.append(order)
        return order

    def sell(
        self,
        symbol: str,
        timestamp: datetime,
        price: float,
        quantity: float | None = None,
    ) -> Order | None:
        position = self.portfolio.positions.get(symbol)
        if position is None or position.quantity <= 0:
            return None

        qty = quantity if quantity is not None else position.quantity
        qty = min(qty, position.quantity)
        if qty <= 0:
            return None

        exec_price = price * (1.0 - self.slippage)
        proceeds = qty * exec_price
        commission_cost = min(self.commission, proceeds)
        net_proceeds = proceeds - commission_cost

        realized = (exec_price - position.avg_entry_price) * qty - commission_cost
        self.portfolio.cash += net_proceeds
        self._realized_pnl += realized

        position.quantity -= qty
        if position.quantity == 0:
            del self.portfolio.positions[symbol]

        order = Order(
            symbol=symbol,
            timestamp=timestamp,
            side=OrderSide.SELL,
            quantity=qty,
            exec_price=exec_price,
            commission=commission_cost,
            realized_pnl=realized,
        )
        self.orders.append(order)
        return order
