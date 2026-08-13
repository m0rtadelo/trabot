from datetime import datetime, timezone

import httpx
import pytest

from app.market.alpaca import AlpacaMarketDataProvider


def make_transport(payloads: list[dict]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["APCA-API-KEY-ID"] == "key"
        assert request.headers["APCA-API-SECRET-KEY"] == "secret"
        return httpx.Response(200, json=payloads.pop(0))

    return httpx.MockTransport(handler)


def test_provider_requires_credentials() -> None:
    with pytest.raises(ValueError):
        AlpacaMarketDataProvider(api_key="", api_secret="")


def test_get_bars_parses_and_normalizes_utc() -> None:
    transport = make_transport(
        [
            {
                "bars": [
                    {
                        "t": "2024-01-02T10:00:00-05:00",
                        "o": 100.0,
                        "h": 105.0,
                        "l": 99.0,
                        "c": 103.0,
                        "v": 1000,
                        "n": 5,
                        "vw": 102.0,
                    }
                ],
                "next_page_token": None,
            }
        ]
    )
    provider = AlpacaMarketDataProvider(
        api_key="key", api_secret="secret", transport=transport
    )

    bars = provider.get_bars(
        symbol="aapl",
        timeframe="1Hour",
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 1, 3, tzinfo=timezone.utc),
    )

    assert len(bars) == 1
    bar = bars[0]
    assert bar.symbol == "AAPL"
    assert bar.timestamp == datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc)
    assert bar.open == 100.0
    assert bar.high == 105.0
    assert bar.low == 99.0
    assert bar.close == 103.0
    assert bar.volume == 1000


def test_get_bars_follows_pagination() -> None:
    page1 = {
        "bars": [
            {
                "t": "2024-01-02T15:00:00Z",
                "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10,
            }
        ],
        "next_page_token": "abc",
    }
    page2 = {
        "bars": [
            {
                "t": "2024-01-02T16:00:00Z",
                "o": 1.0, "h": 2.0, "l": 0.5, "c": 1.5, "v": 10,
            }
        ],
        "next_page_token": None,
    }

    provider = AlpacaMarketDataProvider(
        api_key="key", api_secret="secret", transport=make_transport([page1, page2])
    )

    bars = provider.get_bars(
        symbol="AAPL",
        timeframe="1Hour",
        start=datetime(2024, 1, 1, tzinfo=timezone.utc),
        end=datetime(2024, 1, 3, tzinfo=timezone.utc),
    )

    assert len(bars) == 2


def test_get_bars_raises_on_api_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(422, json={"message": "invalid symbol"})

    provider = AlpacaMarketDataProvider(
        api_key="key", api_secret="secret", transport=httpx.MockTransport(handler)
    )

    with pytest.raises(httpx.HTTPStatusError):
        provider.get_bars(
            symbol="INVALID",
            timeframe="1Hour",
            start=datetime(2024, 1, 1, tzinfo=timezone.utc),
            end=datetime(2024, 1, 3, tzinfo=timezone.utc),
        )
