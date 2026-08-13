from app.portfolio.models import Portfolio


class PositionSizer:
    """Decides how much to invest in a position, separate from the strategy."""

    def __init__(self, max_position_pct: float = 0.20) -> None:
        if not 0.0 < max_position_pct <= 1.0:
            raise ValueError("max_position_pct must be in (0, 1]")
        self.max_position_pct = max_position_pct

    def buy_budget(self, portfolio: Portfolio, symbol: str) -> float:
        total = portfolio.cash + portfolio.cost_basis()
        target = self.max_position_pct * total
        existing = portfolio.positions.get(symbol)
        existing_cost = (
            existing.quantity * existing.avg_entry_price if existing else 0.0
        )
        additional = target - existing_cost
        if additional <= 0.0:
            return 0.0
        return min(additional, portfolio.cash)
