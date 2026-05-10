from __future__ import annotations

import numpy as np
import pandas as pd

from src.analysis.pattern import (
    analyze_multi_timeframe,
    detect_candle_patterns,
    detect_chart_pattern,
    resample_ohlcv,
)


def _make_df(
    *,
    opens: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    closes: np.ndarray,
    volumes: np.ndarray | None = None,
) -> pd.DataFrame:
    n = len(closes)
    if volumes is None:
        volumes = np.full(n, 1000.0, dtype="float64")
    idx = pd.date_range("2024-01-01", periods=n, freq="D", tz="Asia/Taipei")
    return pd.DataFrame(
        {
            "open": opens.astype("float64"),
            "high": highs.astype("float64"),
            "low": lows.astype("float64"),
            "close": closes.astype("float64"),
            "volume": volumes.astype("float64"),
        },
        index=idx,
    )


def _pattern_detected_map(df: pd.DataFrame) -> dict[str, bool]:
    return {item.name: item.detected for item in detect_candle_patterns(df)}


def test_detect_long_red_candle() -> None:
    n = 30
    opens = np.full(n, 100.0)
    closes = np.full(n, 101.0)
    highs = np.full(n, 102.0)
    lows = np.full(n, 99.0)
    opens[-1] = 100.0
    closes[-1] = 110.0
    highs[-1] = 111.0
    lows[-1] = 99.0
    detected = _pattern_detected_map(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert detected["長紅 K"]


def test_detect_long_black_candle() -> None:
    n = 30
    opens = np.full(n, 101.0)
    closes = np.full(n, 100.0)
    highs = np.full(n, 102.0)
    lows = np.full(n, 99.0)
    opens[-1] = 110.0
    closes[-1] = 100.0
    highs[-1] = 111.0
    lows[-1] = 99.0
    detected = _pattern_detected_map(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert detected["長黑 K"]


def test_detect_doji() -> None:
    n = 30
    opens = np.linspace(100, 105, n)
    closes = opens + 0.8
    highs = np.maximum(opens, closes) + 2.0
    lows = np.minimum(opens, closes) - 2.0
    opens[-1] = 100.0
    closes[-1] = 100.0
    highs[-1] = 104.0
    lows[-1] = 96.0
    detected = _pattern_detected_map(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert detected["十字線"]


def test_detect_hammer() -> None:
    n = 30
    closes = np.linspace(120, 95, n)
    opens = closes + 1.0
    highs = np.maximum(opens, closes) + 0.6
    lows = np.minimum(opens, closes) - 0.8
    opens[-1] = 95.5
    closes[-1] = 96.2
    highs[-1] = 96.5
    lows[-1] = 91.5
    detected = _pattern_detected_map(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert detected["錘子"]


def test_detect_engulfing() -> None:
    n = 30
    opens = np.full(n, 100.0)
    closes = np.full(n, 100.5)
    highs = np.full(n, 101.0)
    lows = np.full(n, 99.0)
    opens[-2] = 103.0
    closes[-2] = 101.0
    highs[-2] = 103.5
    lows[-2] = 100.8
    opens[-1] = 100.5
    closes[-1] = 104.0
    highs[-1] = 104.5
    lows[-1] = 100.2
    detected = _pattern_detected_map(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert detected["吞噬"]


def test_no_pattern_detected() -> None:
    n = 30
    opens = np.linspace(100, 105, n)
    closes = opens + 0.5
    highs = closes + 1.0
    lows = opens - 1.0
    detected = _pattern_detected_map(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert not any(detected.values())


def test_w_bottom_detected() -> None:
    n = 70
    opens = np.full(n, 100.0)
    closes = np.full(n, 100.0)
    highs = np.full(n, 103.0)
    lows = np.full(n, 97.0)
    lows[20] = 80.0
    lows[45] = 82.0
    highs[33] = 100.0
    result = detect_chart_pattern(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    w = result[0]
    assert w.pattern_type == "W底（雙底）"
    assert w.formed


def test_w_bottom_not_formed() -> None:
    n = 70
    opens = np.full(n, 100.0)
    closes = np.full(n, 100.0)
    highs = np.full(n, 101.0)
    lows = np.full(n, 98.0)
    lows[20] = 82.0
    lows[45] = 89.0
    result = detect_chart_pattern(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    w = result[0]
    assert not w.formed
    assert "未形成" in w.description


def test_m_top_detected() -> None:
    n = 70
    opens = np.full(n, 100.0)
    closes = np.full(n, 100.0)
    highs = np.full(n, 103.0)
    lows = np.full(n, 97.0)
    highs[18] = 122.0
    highs[44] = 120.0
    lows[32] = 92.0
    result = detect_chart_pattern(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    m = result[1]
    assert m.pattern_type == "M頭（雙頂）"
    assert m.formed


def test_m_top_not_formed() -> None:
    n = 70
    opens = np.full(n, 100.0)
    closes = np.full(n, 100.0)
    highs = np.full(n, 105.0)
    lows = np.full(n, 95.0)
    highs[15] = 110.0
    highs[45] = 115.0
    lows[30] = 104.0
    result = detect_chart_pattern(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    m = result[1]
    assert not m.formed


def test_tolerance_boundary() -> None:
    n = 70
    opens = np.full(n, 100.0)
    closes = np.full(n, 100.0)
    highs = np.full(n, 103.0)
    lows = np.full(n, 97.0)
    lows[20] = 100.0
    lows[45] = 103.045685  # diff / avg ~= 3%
    highs[30] = 108.0
    result = detect_chart_pattern(
        _make_df(opens=opens, highs=highs, lows=lows, closes=closes),
        tolerance_pct=0.03,
    )
    assert result[0].formed


def test_multi_timeframe_bullish() -> None:
    n = 1800
    closes = np.linspace(50, 350, n)
    opens = closes - 0.5
    highs = closes + 1.5
    lows = closes - 1.5
    mtf = analyze_multi_timeframe(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    assert mtf.daily.trend_direction == "多頭"
    assert mtf.weekly.trend_direction == "多頭"
    assert mtf.monthly.trend_direction == "多頭"


def test_multi_timeframe_mixed() -> None:
    n = 1800
    down = np.linspace(320, 100, 1500)
    flat = 100 + 1.0 * np.sin(np.linspace(0, 6 * np.pi, 260))
    up = np.linspace(100, 110, 40)
    closes = np.concatenate([down, flat, up])
    opens = closes + 0.3
    highs = np.maximum(opens, closes) + 1.0
    lows = np.minimum(opens, closes) - 1.0
    mtf = analyze_multi_timeframe(_make_df(opens=opens, highs=highs, lows=lows, closes=closes))
    trends = {mtf.daily.trend_direction, mtf.weekly.trend_direction, mtf.monthly.trend_direction}
    assert trends.issubset({"多頭", "空頭", "盤整"})
    assert len(trends) >= 2


def test_resample_ohlcv_correct() -> None:
    opens = np.array([10, 11, 12, 13, 14, 15, 16], dtype="float64")
    closes = np.array([11, 12, 13, 14, 15, 16, 17], dtype="float64")
    highs = closes + 2
    lows = opens - 2
    volumes = np.array([100, 200, 300, 400, 500, 600, 700], dtype="float64")
    df = _make_df(opens=opens, highs=highs, lows=lows, closes=closes, volumes=volumes)
    weekly = resample_ohlcv(df, freq="W")

    first = weekly.iloc[0]
    chunk = df.iloc[:7]
    assert first["open"] == chunk["open"].iloc[0]
    assert first["high"] == chunk["high"].max()
    assert first["low"] == chunk["low"].min()
    assert first["close"] == chunk["close"].iloc[-1]
    assert first["volume"] == chunk["volume"].sum()


def test_insufficient_data_for_pattern() -> None:
    n = 10
    opens = np.linspace(100, 105, n)
    closes = opens + 0.4
    highs = closes + 1
    lows = opens - 1
    df = _make_df(opens=opens, highs=highs, lows=lows, closes=closes)

    candles = detect_candle_patterns(df)
    charts = detect_chart_pattern(df)
    assert len(candles) > 0
    assert all(not item.formed for item in charts)
