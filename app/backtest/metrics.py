import math

from app.backtest.models import BacktestMetrics, EquityPoint, TradeResult


def total_return(initial_capital: float, final_capital: float) -> float:
    if initial_capital <= 0:
        return 0.0
    return final_capital / initial_capital - 1.0


def annualized_return(
    initial_capital: float,
    final_capital: float,
    first_ts,
    last_ts,
) -> float:
    if initial_capital <= 0 or final_capital <= 0:
        return 0.0
    days = (last_ts - first_ts).total_seconds() / 86400.0
    if days <= 0:
        return 0.0
    years = days / 365.25
    return (final_capital / initial_capital) ** (1.0 / years) - 1.0


def max_drawdown(values: list[float]) -> float:
    peak: float | None = None
    drawdown = 0.0
    for value in values:
        if peak is None or value > peak:
            peak = value
        if peak > 0:
            drawdown = max(drawdown, (peak - value) / peak)
    return drawdown


def sharpe_ratio(
    equity_curve: list[EquityPoint],
    risk_free: float = 0.0,
    periods_per_year: float = 252.0,
) -> float:
    if len(equity_curve) < 2:
        return 0.0

    daily = {}
    for point in equity_curve:
        daily[point.timestamp.date()] = point.value
    values = [daily[day] for day in sorted(daily)]
    if len(values) < 2:
        return 0.0

    returns = [
        (values[i] - values[i - 1]) / values[i - 1]
        for i in range(1, len(values))
        if values[i - 1] > 0
    ]
    if not returns:
        return 0.0

    mean = sum(returns) / len(returns)
    variance = sum((r - mean) ** 2 for r in returns) / len(returns)
    std = math.sqrt(variance)
    if std == 0:
        return 0.0
    return (mean - risk_free) / std * math.sqrt(periods_per_year)


def compute_metrics(
    initial_capital: float,
    equity_curve: list[EquityPoint],
    trades: list[TradeResult],
) -> BacktestMetrics:
    final_capital = equity_curve[-1].value if equity_curve else initial_capital
    wins = [t.pnl for t in trades if t.pnl > 0]
    losses = [t.pnl for t in trades if t.pnl < 0]
    num_trades = len(trades)
    num_wins = len(wins)
    num_losses = len(losses)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))

    return BacktestMetrics(
        initial_capital=initial_capital,
        final_capital=final_capital,
        total_return=total_return(initial_capital, final_capital),
        annualized_return=annualized_return(
            initial_capital,
            final_capital,
            equity_curve[0].timestamp,
            equity_curve[-1].timestamp,
        )
        if equity_curve
        else 0.0,
        max_drawdown=max_drawdown([p.value for p in equity_curve]),
        num_trades=num_trades,
        winning_trades=num_wins,
        losing_trades=num_losses,
        win_rate=num_wins / num_trades if num_trades else 0.0,
        avg_winning_trade=gross_profit / num_wins if num_wins else 0.0,
        avg_losing_trade=gross_loss / num_losses if num_losses else 0.0,
        profit_factor=gross_profit / gross_loss if gross_loss else None,
        sharpe_ratio=sharpe_ratio(equity_curve),
    )
