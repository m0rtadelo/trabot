from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.database.models import Bar, SignalRecord
from app.market.models import BarData
from app.strategy.models import Signal


class BarRepository:
    def __init__(self, session: Session):
        self.session = session

    def save_bars(self, bars: list[BarData]) -> int:
        if not bars:
            return 0

        symbols = {b.symbol for b in bars}
        before = {s: self.count_bars(s) for s in symbols}

        rows = [
            {
                "symbol": b.symbol,
                "timestamp": b.timestamp,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
            }
            for b in bars
        ]

        dialect = self.session.bind.dialect.name
        if dialect == "postgresql":
            stmt = pg_insert(Bar).values(rows).on_conflict_do_nothing(
                index_elements=["symbol", "timestamp"]
            )
        else:
            stmt = sqlite_insert(Bar).values(rows).on_conflict_do_nothing(
                index_elements=["symbol", "timestamp"]
            )

        self.session.execute(stmt)
        self.session.commit()

        after = {s: self.count_bars(s) for s in symbols}
        return sum(after[s] - before[s] for s in symbols)

    def get_bars(
        self,
        symbol: str,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[Bar]:
        stmt = (
            select(Bar)
            .where(Bar.symbol == symbol)
            .order_by(Bar.timestamp.asc())
        )
        if start is not None:
            stmt = stmt.where(Bar.timestamp >= start)
        if end is not None:
            stmt = stmt.where(Bar.timestamp <= end)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))

    def get_latest_bar(self, symbol: str) -> Bar | None:
        stmt = (
            select(Bar)
            .where(Bar.symbol == symbol)
            .order_by(Bar.timestamp.desc())
            .limit(1)
        )
        return self.session.scalar(stmt)

    def count_bars(self, symbol: str) -> int:
        stmt = select(Bar.id).where(Bar.symbol == symbol)
        return len(self.session.scalars(stmt).all())

    def save_signal(self, signal: Signal, strategy_name: str) -> int:
        rows = [
            {
                "symbol": signal.symbol,
                "timestamp": signal.timestamp,
                "strategy": strategy_name,
                "action": signal.action.value,
                "score": signal.score,
                "reason": signal.reason,
            }
        ]
        dialect = self.session.bind.dialect.name
        if dialect == "postgresql":
            stmt = pg_insert(SignalRecord).values(rows).on_conflict_do_nothing(
                index_elements=["symbol", "timestamp", "strategy"]
            )
        else:
            stmt = sqlite_insert(SignalRecord).values(rows).on_conflict_do_nothing(
                index_elements=["symbol", "timestamp", "strategy"]
            )
        result = self.session.execute(stmt)
        self.session.commit()
        return result.rowcount

    def get_signals(
        self,
        symbol: str | None = None,
        start: datetime | None = None,
        end: datetime | None = None,
        limit: int | None = None,
    ) -> list[SignalRecord]:
        stmt = select(SignalRecord).order_by(SignalRecord.timestamp.desc())
        if symbol is not None:
            stmt = stmt.where(SignalRecord.symbol == symbol)
        if start is not None:
            stmt = stmt.where(SignalRecord.timestamp >= start)
        if end is not None:
            stmt = stmt.where(SignalRecord.timestamp <= end)
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.session.scalars(stmt))
