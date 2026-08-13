import pytest

from app.indicators.momentum import rsi
from app.indicators.trend import sma, volume_sma
from app.indicators.volatility import atr


class TestSMA:
    def test_basic(self) -> None:
        assert sma([1, 2, 3, 4, 5], 3) == [None, None, 2.0, 3.0, 4.0]

    def test_window_one(self) -> None:
        assert sma([1, 2, 3], 1) == [1.0, 2.0, 3.0]

    def test_window_equals_length(self) -> None:
        assert sma([1, 2, 3], 3) == [None, None, 2.0]

    def test_window_larger_than_length(self) -> None:
        assert sma([1, 2, 3], 5) == [None, None, None]

    def test_empty(self) -> None:
        assert sma([], 3) == []

    def test_invalid_window(self) -> None:
        with pytest.raises(ValueError):
            sma([1, 2, 3], 0)

    def test_volume_sma(self) -> None:
        assert volume_sma([100, 200, 300, 400], 3) == [None, None, 200.0, 300.0]


class TestRSI:
    WILDER_CLOSES = [
        44.34, 44.09, 44.15, 43.61, 44.33, 44.83, 45.10, 45.42,
        45.84, 46.08, 45.89, 46.03, 45.61, 46.28, 46.28,
    ]

    def test_known_wilder_value(self) -> None:
        result = rsi(self.WILDER_CLOSES, 14)
        assert result[14] == pytest.approx(70.464, abs=0.01)
        assert result[:14] == [None] * 14

    def test_requires_at_least_window_plus_one(self) -> None:
        assert rsi([1, 2, 3], 14) == [None, None, None]

    def test_all_gains_is_100(self) -> None:
        result = rsi([1.0, 2.0, 3.0, 4.0, 5.0], 3)
        assert result[3] == 100.0

    def test_all_losses_is_0(self) -> None:
        result = rsi([5.0, 4.0, 3.0, 2.0, 1.0], 3)
        assert result[3] == 0.0

    def test_flat_series_is_50(self) -> None:
        result = rsi([10.0, 10.0, 10.0, 10.0], 3)
        assert result[3] == 50.0

    def test_empty(self) -> None:
        assert rsi([], 14) == []

    def test_invalid_window(self) -> None:
        with pytest.raises(ValueError):
            rsi([1, 2, 3], 0)


class TestATR:
    HIGHS = [10, 11, 12, 13, 12, 14, 13, 15]
    LOWS = [8, 9, 9, 11, 10, 11, 12, 13]
    CLOSES = [9, 10, 11, 12, 11, 13, 12, 14]

    def test_known_values(self) -> None:
        result = atr(self.HIGHS, self.LOWS, self.CLOSES, 3)
        assert result[:2] == [None, None]
        assert result[2] == pytest.approx(7 / 3)
        assert result[3] == pytest.approx(20 / 9)
        assert result[7] == pytest.approx(1679 / 729)

    def test_not_enough_data(self) -> None:
        assert atr([10], [8], [9], 3) == [None]

    def test_empty(self) -> None:
        assert atr([], [], [], 14) == []

    def test_mismatched_lengths(self) -> None:
        with pytest.raises(ValueError):
            atr([1, 2, 3], [1, 2], [1, 2, 3])

    def test_invalid_window(self) -> None:
        with pytest.raises(ValueError):
            atr([1, 2, 3], [1, 2, 3], [1, 2, 3], 0)
