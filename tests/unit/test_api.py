import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.db import Base, get_session
from app.main import app

engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
Base.metadata.create_all(engine)
TestSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def override_session():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_session] = override_session
client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_portfolio_before_any_run():
    r = client.get("/api/portfolio")
    assert r.status_code == 200
    data = r.json()
    assert data["cash"] == 10000.0
    assert data["positions"] == []
    assert data["total_value"] == 10000.0


def test_positions_before_any_run():
    r = client.get("/api/positions")
    assert r.status_code == 200
    assert r.json()["positions"] == []


def test_signals_before_any_run():
    r = client.get("/api/signals")
    assert r.status_code == 200
    assert r.json()["signals"] == []


def test_status_before_any_run():
    r = client.get("/api/status")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "not_started"
    assert data["last_run_at"] is None


def test_performance_before_any_run():
    r = client.get("/api/performance")
    assert r.status_code == 200
    data = r.json()
    assert data["initial_capital"] == 10000.0
    assert data["current_value"] == 10000.0
    assert data["num_trades"] == 0
