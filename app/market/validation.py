from datetime import datetime, timezone

from app.market.models import BarData


class BarValidationError(ValueError):
    pass


def validate_bars(bars: list[BarData]) -> None:
    previous: datetime | None = None
    for bar in bars:
        if bar.timestamp.tzinfo is None:
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: timestamp must be timezone-aware"
            )
        if bar.timestamp.tzinfo != timezone.utc:
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: timestamp must be in UTC"
            )
        if not (bar.open > 0 and bar.high > 0 and bar.low > 0 and bar.close > 0):
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: prices must be positive"
            )
        if bar.high < max(bar.open, bar.close):
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: high below open/close"
            )
        if bar.low > min(bar.open, bar.close):
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: low above open/close"
            )
        if bar.volume < 0:
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: negative volume"
            )
        if previous is not None and bar.timestamp <= previous:
            raise BarValidationError(
                f"{bar.symbol}@{bar.timestamp}: bars not strictly time-ordered"
            )
        previous = bar.timestamp
