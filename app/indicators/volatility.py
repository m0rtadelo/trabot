from typing import Optional

Number = float


def atr(
    highs: list[Number],
    lows: list[Number],
    closes: list[Number],
    window: int = 14,
) -> list[Optional[float]]:
    if not (len(highs) == len(lows) == len(closes)):
        raise ValueError("highs, lows and closes must have the same length")
    if window < 1:
        raise ValueError("window must be >= 1")

    n = len(highs)
    out: list[Optional[float]] = [None] * n
    if n < window:
        return out

    true_ranges: list[float] = [highs[0] - lows[0]]
    for i in range(1, n):
        true_ranges.append(
            max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
        )

    avg = sum(true_ranges[:window]) / window
    out[window - 1] = avg
    for i in range(window, n):
        avg = (avg * (window - 1) + true_ranges[i]) / window
        out[i] = avg

    return out
