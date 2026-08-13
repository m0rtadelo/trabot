from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass(frozen=True)
class CandleFeatures:
    symbol: str
    timestamp: datetime
    close: float
    volume: int
    sma20: float | None
    sma50: float | None
    sma200: float | None
    rsi14: float | None
    atr14: float | None
    volume_sma20: float | None


@dataclass(frozen=True)
class Signal:
    symbol: str
    timestamp: datetime
    action: SignalAction
    score: float
    reason: list[str]
