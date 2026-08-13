from abc import ABC, abstractmethod

from app.strategy.models import CandleFeatures, Signal, SignalAction


class Strategy(ABC):
    @abstractmethod
    def evaluate(self, features: CandleFeatures) -> Signal:
        ...


class SmaRsiStrategy(Strategy):
    """Deterministic trend + momentum + volume strategy."""

    def evaluate(self, features: CandleFeatures) -> Signal:
        required = [
            features.sma20,
            features.sma50,
            features.sma200,
            features.rsi14,
            features.volume_sma20,
        ]
        if any(v is None for v in required):
            return Signal(
                symbol=features.symbol,
                timestamp=features.timestamp,
                action=SignalAction.HOLD,
                score=0.0,
                reason=["Insufficient data to evaluate"],
            )

        buy_conditions = [
            features.sma20 > features.sma50,
            features.sma50 > features.sma200,
            features.rsi14 > 50,
            features.rsi14 < 70,
            features.volume > features.volume_sma20,
        ]
        if all(buy_conditions):
            return Signal(
                symbol=features.symbol,
                timestamp=features.timestamp,
                action=SignalAction.BUY,
                score=sum(buy_conditions) / len(buy_conditions),
                reason=[
                    "SMA20 above SMA50",
                    "SMA50 above SMA200",
                    "RSI in bullish range",
                    "Volume above average",
                ],
            )

        sell_reasons: list[str] = []
        if features.sma20 < features.sma50:
            sell_reasons.append("SMA20 below SMA50")
        if features.rsi14 < 40:
            sell_reasons.append("RSI below 40")
        if sell_reasons:
            sell_conditions = [
                features.sma20 < features.sma50,
                features.rsi14 < 40,
            ]
            return Signal(
                symbol=features.symbol,
                timestamp=features.timestamp,
                action=SignalAction.SELL,
                score=sum(sell_conditions) / len(sell_conditions),
                reason=sell_reasons,
            )

        return Signal(
            symbol=features.symbol,
            timestamp=features.timestamp,
            action=SignalAction.HOLD,
            score=0.0,
            reason=["No BUY or SELL conditions met"],
        )
