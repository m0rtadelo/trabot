from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.live import run_cycle
from app.config.settings import get_settings
from app.database.db import get_session
from app.database.repository import BarRepository
from app.market.alpaca import AlpacaMarketDataProvider
from app.market.models import BarData
from app.strategy.strategy import SmaRsiStrategy

router = APIRouter()
api_router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@api_router.post("/run")
def api_run(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    strategy = SmaRsiStrategy()
    result = run_cycle(session, settings, strategy)
    return result


@api_router.get("/portfolio")
def api_portfolio(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    repo = BarRepository(session)
    state = repo.load_live_state()
    if state is None:
        return {
            "cash": settings.initial_capital,
            "positions": [],
            "total_value": settings.initial_capital,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
        }

    current_prices = {}
    for symbol in settings.symbol_list:
        bar = repo.get_latest_bar(symbol)
        if bar:
            current_prices[symbol] = bar.close

    positions = []
    total_market = 0.0
    total_unrealized = 0.0
    for sym, p in state.get("positions", {}).items():
        price = current_prices.get(sym, p["avg_entry_price"])
        mv = p["quantity"] * price
        upnl = p["quantity"] * (price - p["avg_entry_price"])
        total_market += mv
        total_unrealized += upnl
        positions.append({
            "symbol": sym,
            "quantity": p["quantity"],
            "avg_entry_price": p["avg_entry_price"],
            "current_price": price,
            "market_value": round(mv, 2),
            "unrealized_pnl": round(upnl, 2),
        })

    return {
        "cash": round(state["cash"], 2),
        "positions": positions,
        "total_value": round(state["cash"] + total_market, 2),
        "realized_pnl": round(state.get("realized_pnl", 0.0), 2),
        "unrealized_pnl": round(total_unrealized, 2),
    }


@api_router.get("/positions")
def api_positions(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    repo = BarRepository(session)
    state = repo.load_live_state()
    if state is None:
        return {"positions": []}

    current_prices = {}
    for symbol in settings.symbol_list:
        bar = repo.get_latest_bar(symbol)
        if bar:
            current_prices[symbol] = bar.close

    positions = []
    for sym, p in state.get("positions", {}).items():
        price = current_prices.get(sym, p["avg_entry_price"])
        positions.append({
            "symbol": sym,
            "quantity": p["quantity"],
            "avg_entry_price": p["avg_entry_price"],
            "current_price": price,
            "market_value": round(p["quantity"] * price, 2),
            "unrealized_pnl": round(p["quantity"] * (price - p["avg_entry_price"]), 2),
        })
    return {"positions": positions}


@api_router.get("/signals")
def api_signals(
    limit: int = 50,
    session: Session = Depends(get_session),
) -> dict:
    repo = BarRepository(session)
    records = repo.get_signals(limit=limit)
    return {
        "signals": [
            {
                "symbol": r.symbol,
                "timestamp": r.timestamp.isoformat(),
                "action": r.action,
                "score": r.score,
                "reason": r.reason,
                "strategy": r.strategy,
            }
            for r in records
        ]
    }


@api_router.get("/performance")
def api_performance(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    repo = BarRepository(session)
    state = repo.load_live_state()
    if state is None:
        return {
            "initial_capital": settings.initial_capital,
            "current_value": settings.initial_capital,
            "realized_pnl": 0.0,
            "unrealized_pnl": 0.0,
            "total_pnl": 0.0,
            "total_return_pct": 0.0,
            "max_drawdown_pct": 0.0,
            "num_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate": 0.0,
        }

    current_prices = {}
    for symbol in settings.symbol_list:
        bar = repo.get_latest_bar(symbol)
        if bar:
            current_prices[symbol] = bar.close

    total_market = 0.0
    total_unrealized = 0.0
    for sym, p in state.get("positions", {}).items():
        price = current_prices.get(sym, p["avg_entry_price"])
        total_market += p["quantity"] * price
        total_unrealized += p["quantity"] * (price - p["avg_entry_price"])

    current_value = state["cash"] + total_market
    peak = state.get("peak_value", current_value)
    max_dd = (peak - current_value) / peak if peak > 0 else 0.0

    sell_orders = [o for o in state.get("order_history", []) if o["side"] == "SELL"]
    wins = [o for o in sell_orders if (o.get("realized_pnl") or 0) > 0]
    losses = [o for o in sell_orders if (o.get("realized_pnl") or 0) < 0]
    num = len(sell_orders)

    initial = settings.initial_capital
    return {
        "initial_capital": initial,
        "current_value": round(current_value, 2),
        "realized_pnl": round(state.get("realized_pnl", 0.0), 2),
        "unrealized_pnl": round(total_unrealized, 2),
        "total_pnl": round(state.get("realized_pnl", 0.0) + total_unrealized, 2),
        "total_return_pct": round((current_value / initial - 1.0) * 100, 2) if initial > 0 else 0.0,
        "max_drawdown_pct": round(max_dd * 100, 2),
        "num_trades": num,
        "winning_trades": len(wins),
        "losing_trades": len(losses),
        "win_rate": round(len(wins) / num * 100, 1) if num > 0 else 0.0,
    }


@api_router.get("/status")
def api_status(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    repo = BarRepository(session)
    state = repo.load_live_state()
    if state is None:
        return {
            "status": "not_started",
            "last_run_at": None,
            "last_candle": None,
            "last_run_status": None,
            "last_error": None,
        }
    return {
        "status": state.get("last_run_status", "not_started"),
        "last_run_at": state.get("last_run_at"),
        "last_candle": state.get("last_candle_timestamp"),
        "last_error": state.get("last_error"),
    }
