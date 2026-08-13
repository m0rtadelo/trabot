from typing import Optional

Number = float


def sma(values: list[Number], window: int) -> list[Optional[float]]:
    if window < 1:
        raise ValueError("window must be >= 1")

    out: list[Optional[float]] = [None] * len(values)
    running = 0.0
    for i, value in enumerate(values):
        running += value
        if i >= window:
            running -= values[i - window]
        if i >= window - 1:
            out[i] = running / window
    return out


def volume_sma(volumes: list[int], window: int = 20) -> list[Optional[float]]:
    return sma([float(v) for v in volumes], window)
