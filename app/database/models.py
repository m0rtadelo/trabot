from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.db import Base


class Bar(Base):
    __tablename__ = "bars"
    __table_args__ = (
        UniqueConstraint("symbol", "timestamp", name="uq_bar_symbol_timestamp"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[int] = mapped_column(Integer)


class SignalRecord(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint(
            "symbol", "timestamp", "strategy", name="uq_signal_symbol_timestamp_strategy"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    strategy: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(8))
    score: Mapped[float] = mapped_column(Float)
    reason: Mapped[list] = mapped_column(JSON)


class BacktestRecord(Base):
    __tablename__ = "backtests"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    strategy: Mapped[str] = mapped_column(String(64))
    symbols: Mapped[str] = mapped_column(String(512))
    start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    initial_capital: Mapped[float] = mapped_column(Float)
    commission: Mapped[float] = mapped_column(Float)
    slippage_bps: Mapped[int] = mapped_column(Integer)
    metrics: Mapped[dict] = mapped_column(JSON)
    buy_and_hold_return: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EquityPointRecord(Base):
    __tablename__ = "equity_curve"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("backtests.id"), index=True
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    value: Mapped[float] = mapped_column(Float)


class TradeRecord(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    backtest_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("backtests.id"), index=True
    )
    symbol: Mapped[str] = mapped_column(String(16))
    entry_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exit_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float] = mapped_column(Float)
    quantity: Mapped[float] = mapped_column(Float)
    pnl: Mapped[float] = mapped_column(Float)
