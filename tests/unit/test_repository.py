from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.db import Base
from app.database.repository import BarRepository
from app.market.models import BarData


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


def make_bars(symbol: str = "AAPL", start: int = 0, count: int = 3) -> list[BarData]:
    base = datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)
    return [
        BarData(
            symbol=symbol,
            timestamp=base + timedelta(hours=i + start),
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1000,
        )
        for i in range(count)
    ]


def test_save_and_count(session) -> None:
    repo = BarRepository(session)
    inserted = repo.save_bars(make_bars())
    assert inserted == 3
    assert repo.count_bars("AAPL") == 3


def test_save_is_idempotent(session) -> None:
    repo = BarRepository(session)
    bars = make_bars()
    assert repo.save_bars(bars) == 3
    assert repo.save_bars(bars) == 0
    assert repo.count_bars("AAPL") == 3


def test_save_partial_overlap(session) -> None:
    repo = BarRepository(session)
    assert repo.save_bars(make_bars(count=2)) == 2
    assert repo.save_bars(make_bars(count=3)) == 1
    assert repo.count_bars("AAPL") == 3


def test_get_bars_ordered_and_filtered(session) -> None:
    repo = BarRepository(session)
    repo.save_bars(make_bars(count=5))
    bars = repo.get_bars(
        "AAPL",
        start=datetime(2024, 1, 2, 16, 0, tzinfo=timezone.utc),
    )
    assert [b.timestamp.hour for b in bars] == [16, 17, 18, 19]


def test_get_latest_bar(session) -> None:
    repo = BarRepository(session)
    repo.save_bars(make_bars(count=5))
    latest = repo.get_latest_bar("AAPL")
    assert latest is not None
    assert latest.timestamp.hour == 19


def test_symbols_are_independent(session) -> None:
    repo = BarRepository(session)
    repo.save_bars(make_bars(symbol="AAPL"))
    repo.save_bars(make_bars(symbol="MSFT"))
    assert repo.count_bars("AAPL") == 3
    assert repo.count_bars("MSFT") == 3


def test_empty_save(session) -> None:
    repo = BarRepository(session)
    assert repo.save_bars([]) == 0
