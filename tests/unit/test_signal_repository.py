from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.db import Base
from app.database.repository import BarRepository
from app.strategy.models import Signal, SignalAction


@pytest.fixture()
def session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = Session()
    try:
        yield db
    finally:
        db.close()


def make_signal(action: SignalAction = SignalAction.BUY) -> Signal:
    return Signal(
        symbol="AAPL",
        timestamp=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
        action=action,
        score=0.75,
        reason=["SMA20 above SMA50", "Volume above average"],
    )


def test_save_signal(session) -> None:
    repo = BarRepository(session)
    repo.save_signal(make_signal(), strategy_name="sma_rsi")
    signals = repo.get_signals()
    assert len(signals) == 1
    assert signals[0].symbol == "AAPL"
    assert signals[0].strategy == "sma_rsi"
    assert signals[0].action == "BUY"
    assert signals[0].score == 0.75
    assert signals[0].reason == ["SMA20 above SMA50", "Volume above average"]


def test_save_signal_is_idempotent(session) -> None:
    repo = BarRepository(session)
    repo.save_signal(make_signal(), strategy_name="sma_rsi")
    repo.save_signal(make_signal(), strategy_name="sma_rsi")
    assert len(repo.get_signals()) == 1


def test_same_candle_different_strategies_coexist(session) -> None:
    repo = BarRepository(session)
    repo.save_signal(make_signal(), strategy_name="sma_rsi")
    repo.save_signal(make_signal(SignalAction.HOLD), strategy_name="other")
    assert len(repo.get_signals()) == 2


def test_get_signals_filtered_by_symbol(session) -> None:
    repo = BarRepository(session)
    aapl = make_signal()
    repo.save_signal(aapl, strategy_name="sma_rsi")
    msft = Signal(
        symbol="MSFT",
        timestamp=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
        action=SignalAction.HOLD,
        score=0.0,
        reason=[],
    )
    repo.save_signal(msft, strategy_name="sma_rsi")
    assert len(repo.get_signals(symbol="AAPL")) == 1
