from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.backtest.models import (
    BacktestMetrics,
    BacktestParams,
    BacktestResult,
    EquityPoint,
    TradeResult,
)
from app.database.db import Base
from app.database.models import EquityPointRecord, TradeRecord
from app.database.repository import BarRepository

BASE = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)


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


def make_result() -> BacktestResult:
    params = BacktestParams(
        strategy="sma_rsi",
        symbols=["AAPL"],
        start=BASE,
        end=BASE + timedelta(hours=2),
        initial_capital=1000.0,
        commission=0.0,
        slippage_bps=5,
    )
    metrics = BacktestMetrics(
        initial_capital=1000.0,
        final_capital=1100.0,
        total_return=0.1,
        annualized_return=0.5,
        max_drawdown=0.05,
        num_trades=1,
        winning_trades=1,
        losing_trades=0,
        win_rate=1.0,
        avg_winning_trade=100.0,
        avg_losing_trade=0.0,
        profit_factor=100.0,
        sharpe_ratio=1.5,
    )
    equity = [
        EquityPoint(BASE, 1000.0),
        EquityPoint(BASE + timedelta(hours=1), 1050.0),
        EquityPoint(BASE + timedelta(hours=2), 1100.0),
    ]
    trades = [
        TradeResult("AAPL", BASE, BASE + timedelta(hours=2), 100.0, 110.0, 10.0, 100.0)
    ]
    return BacktestResult(
        backtest_id="backtest-123",
        params=params,
        metrics=metrics,
        equity_curve=equity,
        trades=trades,
        buy_and_hold_final=1200.0,
        buy_and_hold_return=0.2,
    )


def test_save_and_load_backtest(session) -> None:
    repo = BarRepository(session)
    repo.save_backtest_result(make_result())

    record = repo.get_backtest("backtest-123")
    assert record is not None
    assert record.strategy == "sma_rsi"
    assert record.metrics["total_return"] == 0.1
    assert record.buy_and_hold_return == 0.2
    assert record.symbols == "AAPL"

    equity = session.scalars(
        select(EquityPointRecord).where(
            EquityPointRecord.backtest_id == "backtest-123"
        )
    ).all()
    assert len(equity) == 3

    trades = session.scalars(
        select(TradeRecord).where(TradeRecord.backtest_id == "backtest-123")
    ).all()
    assert len(trades) == 1
    assert trades[0].symbol == "AAPL"
    assert trades[0].pnl == 100.0


def test_get_missing_backtest_returns_none(session) -> None:
    repo = BarRepository(session)
    assert repo.get_backtest("nope") is None
