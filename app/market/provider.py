from abc import ABC, abstractmethod
from datetime import datetime

from app.market.models import BarData


class MarketDataProvider(ABC):
    @abstractmethod
    def get_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> list[BarData]:
        ...
