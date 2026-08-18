from datetime import datetime, timezone

import httpx

from app.market.models import BarData
from app.market.provider import MarketDataProvider

DEFAULT_ALPACA_DATA_URL = "https://data.alpaca.markets"


class AlpacaMarketDataProvider(MarketDataProvider):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = DEFAULT_ALPACA_DATA_URL,
        data_feed: str = "iex",
        timeout: float = 30.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        if not api_key or not api_secret:
            raise ValueError("Alpaca API key and secret are required")
        self._data_feed = data_feed
        self._client = httpx.Client(
            base_url=base_url,
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            },
            timeout=timeout,
            transport=transport,
        )

    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[BarData]:
        bars: list[BarData] = []
        page_token: str | None = None

        while True:
            params = {
                "timeframe": timeframe,
                "start": start.isoformat(),
                "end": end.isoformat(),
                "limit": 10000,
                "adjustment": "raw",
                "feed": self._data_feed,
            }
            if page_token:
                params["next_page_token"] = page_token

            response = self._client.get(
                f"/v2/stocks/{symbol.upper()}/bars",
                params=params,
            )
            response.raise_for_status()
            payload = response.json()

            for raw in payload.get("bars", []):
                bars.append(
                    BarData(
                        symbol=symbol.upper(),
                        timestamp=self._parse_timestamp(raw["t"]),
                        open=float(raw["o"]),
                        high=float(raw["h"]),
                        low=float(raw["l"]),
                        close=float(raw["c"]),
                        volume=int(raw["v"]),
                    )
                )

            page_token = payload.get("next_page_token")
            if not page_token:
                break

        return bars

    @staticmethod
    def _parse_timestamp(value: str) -> datetime:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
