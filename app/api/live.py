import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.database.repository import BarRepository
from app.market.alpaca import AlpacaMarketDataProvider
from app.market.models import BarData
from app.market.validation import BarValidationError, validate_bars
from app.market.timeframe import drop_incomplete_bars
from app.portfolio.models import Portfolio, Position
from app.portfolio.simulator import Simulator
from app.strategy.features import compute_features
from app.strategy.models import SignalAction
from app.strategy.strategy import Strategy

logger = logging.getLogger("trading_bot.live")


def fresh_state(initial_capital: float) -> dict:
    return {
        "cash": initial_capital,
        "positions": {},
        "pending": {},
        "realized_pnl": 0.0,
        "peak_value": initial_capital,
        "order_history": [],
        "last_candle_timestamp": None,
        "last_run_at": None,
        "last_run_status": "ok",
        "last_error": None,
    }


def state_to_simulator(state: dict, settings: Settings) -> Simulator:
    sim = Simulator(
        initial_capital=state["cash"],
        commission=settings.commission,
        slippage_bps=settings.slippage_bps,
    )
    sim.portfolio = Portfolio(
        cash=state["cash"],
        positions={
            sym: Position(
                symbol=sym,
                quantity=p["quantity"],
                avg_entry_price=p["avg_entry_price"],
            )
            for sym, p in state.get("positions", {}).items()
        },
    )
    sim._realized_pnl = state.get("realized_pnl", 0.0)
    for entry in state.get("order_history", []):
        from app.portfolio.models import Order, OrderSide
        sim.orders.append(
            Order(
                symbol=entry["symbol"],
                timestamp=datetime.fromisoformat(entry["timestamp"]),
                side=OrderSide(entry["side"]),
                quantity=entry["quantity"],
                exec_price=entry["exec_price"],
                commission=entry["commission"],
                realized_pnl=entry.get("realized_pnl"),
            )
        )
    return sim


def simulator_to_state(sim: Simulator, state: dict) -> dict:
    state["cash"] = sim.portfolio.cash
    state["positions"] = {
        sym: {"quantity": p.quantity, "avg_entry_price": p.avg_entry_price}
        for sym, p in sim.portfolio.positions.items()
    }
    state["realized_pnl"] = sim.realized_pnl
    state["order_history"] = [
        {
            "symbol": o.symbol,
            "timestamp": o.timestamp.isoformat(),
            "side": o.side.value,
            "quantity": o.quantity,
            "exec_price": o.exec_price,
            "commission": o.commission,
            "realized_pnl": o.realized_pnl,
        }
        for o in sim.orders
    ]
    return state


def run_cycle(
    session: Session,
    settings: Settings,
    strategy: Strategy,
) -> dict:
    repo = BarRepository(session)
    state = repo.load_live_state() or fresh_state(settings.initial_capital)

    provider = AlpacaMarketDataProvider(
        api_key=settings.alpaca_api_key,
        api_secret=settings.alpaca_api_secret,
        data_feed=settings.alpaca_data_feed,
    )

    now = datetime.now(timezone.utc)
    start = now - timedelta(days=7)

    fetched_bars: list[BarData] = []
    for symbol in settings.symbol_list:
        try:
            bars = provider.get_bars(symbol, settings.timeframe, start, now)
            fetched_bars.extend(
                drop_incomplete_bars(bars, settings.timeframe, now)
            )
        except Exception as exc:
            logger.error("fetch failed symbol=%s error=%s", symbol, exc)
            state["last_run_status"] = "error"
            state["last_error"] = str(exc)
            state["last_run_at"] = now.isoformat()
            repo.save_live_state(state)
            return {"status": "error", "message": str(exc)}

    try:
        validate_bars(fetched_bars)
    except BarValidationError as exc:
        state["last_run_status"] = "error"
        state["last_error"] = str(exc)
        state["last_run_at"] = now.isoformat()
        repo.save_live_state(state)
        return {"status": "error", "message": str(exc)}

    repo.save_bars(fetched_bars)

    latest_ts_map: dict[str, datetime] = {}
    for symbol in settings.symbol_list:
        latest = repo.get_latest_bar(symbol)
        if latest:
            latest_ts_map[symbol] = latest.timestamp

    new_timestamp = max(latest_ts_map.values()) if latest_ts_map else None
    if new_timestamp is None:
        return {"status": "ok", "message": "no data available"}

    last_candle = state.get("last_candle_timestamp")
    if last_candle and new_timestamp.isoformat() == last_candle:
        return {"status": "ok", "message": "no new data"}

    sim = state_to_simulator(state, settings)

    for symbol in list(state.get("pending", {})):
        if symbol not in latest_ts_map:
            continue
        bar = repo.get_bars(symbol, start=new_timestamp, end=new_timestamp, limit=1)
        if not bar:
            continue
        pending_action = state["pending"].pop(symbol)
        from app.portfolio.models import OrderSide
        if pending_action == "BUY":
            order = sim.buy(symbol, new_timestamp, bar[0].open)
        else:
            order = sim.sell(symbol, new_timestamp, bar[0].open)

    for symbol in settings.symbol_list:
        if symbol not in latest_ts_map:
            continue
        bars = repo.get_bars(symbol, limit=250)
        if len(bars) < 20:
            continue
        bar_data = [
            BarData(
                symbol=b.symbol,
                timestamp=b.timestamp,
                open=b.open,
                high=b.high,
                low=b.low,
                close=b.close,
                volume=b.volume,
            )
            for b in bars
        ]
        features = compute_features(bar_data)
        latest_features = features[-1]
        signal = strategy.evaluate(latest_features)

        has_position = symbol in sim.portfolio.positions
        if signal.action == SignalAction.BUY and not has_position:
            state.setdefault("pending", {})[symbol] = "BUY"
            repo.save_signal(signal, strategy.__class__.__name__)
        elif signal.action == SignalAction.SELL and has_position:
            state.setdefault("pending", {})[symbol] = "SELL"
            repo.save_signal(signal, strategy.__class__.__name__)

    current_prices = {}
    for symbol in settings.symbol_list:
        bar = repo.get_latest_bar(symbol)
        if bar:
            current_prices[symbol] = bar.close

    total_value = sim.portfolio.total_value(current_prices)
    state["peak_value"] = max(state.get("peak_value", total_value), total_value)
    state = simulator_to_state(sim, state)
    state["last_candle_timestamp"] = new_timestamp.isoformat()
    state["last_run_at"] = now.isoformat()
    state["last_run_status"] = "ok"
    state["last_error"] = None
    repo.save_live_state(state)

    return {
        "status": "ok",
        "last_candle": new_timestamp.isoformat(),
        "total_value": round(total_value, 2),
        "cash": round(sim.portfolio.cash, 2),
        "positions": len(sim.portfolio.positions),
        "pending": len(state.get("pending", {})),
    }
