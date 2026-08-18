from datetime import datetime, timezone

from app.api.live import fresh_state, simulator_to_state, state_to_simulator
from app.config.settings import get_settings
from app.portfolio.simulator import Simulator


def test_fresh_state():
    state = fresh_state(1000.0)
    assert state["cash"] == 1000.0
    assert state["positions"] == {}
    assert state["pending"] == {}
    assert state["realized_pnl"] == 0.0
    assert state["peak_value"] == 1000.0
    assert state["order_history"] == []
    assert state["last_candle_timestamp"] is None


def test_roundtrip_state():
    settings = get_settings()
    sim = Simulator(initial_capital=1000.0, commission=0.0, slippage_bps=0)
    ts = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)
    sim.buy("AAPL", ts, 100.0)

    state = {
        "cash": sim.portfolio.cash,
        "positions": {},
        "pending": {},
        "realized_pnl": 0.0,
        "peak_value": 1000.0,
        "order_history": [],
        "last_candle_timestamp": None,
        "last_run_at": None,
        "last_run_status": "ok",
        "last_error": None,
    }
    from app.api.live import simulator_to_state
    state = simulator_to_state(sim, state)

    sim2 = state_to_simulator(state, settings)
    assert sim2.portfolio.cash == sim.portfolio.cash
    assert "AAPL" in sim2.portfolio.positions
    assert sim2.portfolio.positions["AAPL"].quantity == sim.portfolio.positions["AAPL"].quantity
    assert sim2.portfolio.positions["AAPL"].avg_entry_price == sim.portfolio.positions["AAPL"].avg_entry_price
    assert len(sim2.orders) == len(sim.orders)
