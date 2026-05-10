from __future__ import annotations

import re

import numpy as np
import pandas as pd

from src.analysis.technical_summary import generate_technical_summary


def _make_ohlcv_df(closes: np.ndarray, volumes: np.ndarray | None = None) -> pd.DataFrame:
    closes = np.asarray(closes, dtype="float64")
    n = len(closes)
    highs = closes + 2.0
    lows = np.maximum(closes - 2.0, 0.01)
    opens = closes - 0.5
    if volumes is None:
        volumes = np.full(n, 1000.0, dtype="float64")
    index = pd.date_range("2024-01-01", periods=n, freq="D", tz="Asia/Taipei")
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": np.asarray(volumes, dtype="float64"),
        },
        index=index,
    )


def _make_bullish_df(n: int = 120) -> pd.DataFrame:
    closes = np.linspace(100, 220, n)
    volumes = np.linspace(1000, 1800, n)
    return _make_ohlcv_df(closes=closes, volumes=volumes)


def _make_bearish_df(n: int = 120) -> pd.DataFrame:
    closes = np.linspace(220, 100, n)
    volumes = np.linspace(1800, 1000, n)
    return _make_ohlcv_df(closes=closes, volumes=volumes)


def _make_consolidation_df(n: int = 120) -> pd.DataFrame:
    phase = np.linspace(0, 12 * np.pi, n)
    closes = 100 + 2.2 * np.sin(phase)
    volumes = 1000 + 50 * np.cos(phase)
    return _make_ohlcv_df(closes=closes, volumes=volumes)


def test_bullish_trend_fixture() -> None:
    summary = generate_technical_summary(_make_bullish_df())
    assert summary.trend_direction == "多頭趨勢"
    assert "多頭排列" in summary.ma_status
    assert summary.kd_status != "資料不足"
    assert summary.macd_status.startswith("正值")


def test_bearish_trend_fixture() -> None:
    summary = generate_technical_summary(_make_bearish_df())
    assert summary.trend_direction == "空頭趨勢"
    assert "空頭排列" in summary.ma_status
    assert summary.kd_status != "資料不足"
    assert summary.macd_status.startswith("負值")


def test_consolidation_fixture() -> None:
    summary = generate_technical_summary(_make_consolidation_df())
    assert summary.trend_direction == "盤整"
    assert summary.short_term_label in {"中性", "中等偏多", "偏空", "強勢偏多"}


def test_short_term_score_range() -> None:
    summary = generate_technical_summary(_make_bullish_df())
    assert 0.0 <= summary.short_term_score <= 1.0


def test_short_term_score_weights() -> None:
    summary = generate_technical_summary(_make_bullish_df())
    components = summary.short_term_components
    expected = (
        components["ma"] * 0.30
        + components["kd"] * 0.25
        + components["volume_price"] * 0.25
        + components["breakout"] * 0.20
    )
    assert summary.short_term_score == round(expected, 4)


def test_resistance_levels_found() -> None:
    summary = generate_technical_summary(_make_bullish_df())
    assert len(summary.resistance_levels) >= 1
    assert all(level.kind == "resistance" for level in summary.resistance_levels)
    assert any(level.label in {"近60日高點", "近20日高點"} for level in summary.resistance_levels)


def test_support_levels_found() -> None:
    summary = generate_technical_summary(_make_bullish_df())
    assert len(summary.support_levels) >= 2
    assert all(level.kind == "support" for level in summary.support_levels)
    assert any(level.label == "MA20" for level in summary.support_levels)


def test_volume_status_high() -> None:
    base = _make_bullish_df()
    base.loc[base.index[-1], "volume"] = float(base["volume"].tail(5).mean() * 2.0)
    summary = generate_technical_summary(base)
    assert summary.volume_status == "量能放大"


def test_volume_status_low() -> None:
    base = _make_bullish_df()
    base.loc[base.index[-1], "volume"] = float(base["volume"].tail(5).mean() * 0.5)
    summary = generate_technical_summary(base)
    assert summary.volume_status == "量能略縮"


def test_insufficient_data_5bars() -> None:
    df = _make_ohlcv_df(np.array([100, 101, 102, 103, 104], dtype="float64"))
    summary = generate_technical_summary(df)
    assert "資料不足" in summary.ma_status
    assert summary.kd_status == "資料不足"
    assert summary.macd_status == "資料不足"


def test_all_nan_data() -> None:
    n = 10
    df = pd.DataFrame(
        {
            "open": [np.nan] * n,
            "high": [np.nan] * n,
            "low": [np.nan] * n,
            "close": [np.nan] * n,
            "volume": [np.nan] * n,
        },
        index=pd.date_range("2024-01-01", periods=n, freq="D", tz="Asia/Taipei"),
    )
    summary = generate_technical_summary(df)
    assert summary.trend_direction == "資料不足"
    assert summary.ma_bias == "資料不足"
    assert summary.volume_status == "資料不足"


def test_ma_bias_calculation() -> None:
    closes = np.concatenate([np.full(59, 100.0), np.array([120.0])])
    summary = generate_technical_summary(_make_ohlcv_df(closes))
    match = re.search(r"([+-]\d+\.\d+)%", summary.ma_bias)
    assert match is not None
    parsed = float(match.group(1))
    expected_ma20 = (19 * 100.0 + 120.0) / 20.0
    expected_bias = (120.0 - expected_ma20) / expected_ma20 * 100.0
    assert parsed == round(expected_bias, 2)


def test_chip_behavior_injection() -> None:
    chip_text = "外資連三日買超"
    summary = generate_technical_summary(_make_bullish_df(), chip_behavior=chip_text)
    assert summary.chip_behavior == chip_text
