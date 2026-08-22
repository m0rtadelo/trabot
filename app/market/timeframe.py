import re
from datetime import datetime, timedelta

from app.market.models import BarData

_PATTERN = re.compile(r"^(\d+)(Min|Hour|Day|Week)$")


def parse_timeframe(timeframe: str) -> timedelta:
    match = _PATTERN.match(timeframe)
    if not match:
        raise ValueError(f"unsupported timeframe: {timeframe}")
    count = int(match.group(1))
    unit = match.group(2)
    if unit == "Min":
        return timedelta(minutes=count)
    if unit == "Hour":
        return timedelta(hours=count)
    if unit == "Day":
        return timedelta(days=count)
    return timedelta(weeks=count)


def is_bar_complete(timestamp: datetime, timeframe: str, now: datetime) -> bool:
    return timestamp + parse_timeframe(timeframe) <= now


def drop_incomplete_bars(
    bars: list[BarData],
    timeframe: str,
    now: datetime,
) -> list[BarData]:
    return [b for b in bars if is_bar_complete(b.timestamp, timeframe, now)]
