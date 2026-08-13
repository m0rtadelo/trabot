from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, Integer, String, UniqueConstraint
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
