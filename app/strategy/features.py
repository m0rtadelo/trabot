from app.indicators.momentum import rsi
from app.indicators.trend import sma, volume_sma
from app.indicators.volatility import atr
from app.market.models import BarData
from app.strategy.models import CandleFeatures


def compute_features(bars: list[BarData]) -> list[CandleFeatures]:
    closes = [b.close for b in bars]
    highs = [b.high for b in bars]
    lows = [b.low for b in bars]
    volumes = [b.volume for b in bars]

    sma20 = sma(closes, 20)
    sma50 = sma(closes, 50)
    sma200 = sma(closes, 200)
    rsi14 = rsi(closes, 14)
    atr14 = atr(highs, lows, closes, 14)
    vol_sma20 = volume_sma(volumes, 20)

    return [
        CandleFeatures(
            symbol=bar.symbol,
            timestamp=bar.timestamp,
            close=bar.close,
            volume=bar.volume,
            sma20=sma20[i],
            sma50=sma50[i],
            sma200=sma200[i],
            rsi14=rsi14[i],
            atr14=atr14[i],
            volume_sma20=vol_sma20[i],
        )
        for i, bar in enumerate(bars)
    ]
