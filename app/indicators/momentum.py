from typing import Optional

Number = float


def rsi(values: list[Number], window: int = 14) -> list[Optional[float]]:
    if window < 1:
        raise ValueError("window must be >= 1")

    n = len(values)
    out: list[Optional[float]] = [None] * n
    if n < window + 1:
        return out

    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, n):
        delta = values[i] - values[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    out[window] = _to_rsi(avg_gain, avg_loss)

    for i in range(window + 1, n):
        avg_gain = (avg_gain * (window - 1) + gains[i - 1]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i - 1]) / window
        out[i] = _to_rsi(avg_gain, avg_loss)

    return out


def _to_rsi(avg_gain: float, avg_loss: float) -> float:
    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - 100.0 / (1.0 + rs)
