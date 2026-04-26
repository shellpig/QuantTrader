from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.indicators.calculator import IndicatorEngine


def _load_fixture() -> pd.DataFrame:
    fixture_path = Path(__file__).parent / "fixtures" / "ma_cross_data.csv"
    df = pd.read_csv(fixture_path)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df


def test_rsi_range() -> None:
    engine = IndicatorEngine()
    df = _load_fixture()

    out = engine.calculate(df, "RSI_14")
    assert "RSI_14" in out.columns
    non_na = out["RSI_14"].dropna()
    assert not non_na.empty
    assert non_na.between(0, 100).all()


def test_macd_three_columns() -> None:
    engine = IndicatorEngine()
    out = engine.calculate(_load_fixture(), "MACD")
    assert out.columns.tolist() == ["macd", "signal", "histogram"]


def test_kd_alias() -> None:
    engine = IndicatorEngine()
    out = engine.calculate(_load_fixture(), "KD")
    assert out.columns.tolist() == ["K", "D"]


def test_ma_dynamic_parsing() -> None:
    engine = IndicatorEngine()
    data = _load_fixture()

    out_5 = engine.calculate(data, "MA_5")
    out_20 = engine.calculate(data, "MA_20")
    out_60 = engine.calculate(data, "MA_60")

    assert out_5.columns.tolist() == ["MA_5"]
    assert out_20.columns.tolist() == ["MA_20"]
    assert out_60.columns.tolist() == ["MA_60"]
    assert out_5["MA_5"].notna().sum() > out_60["MA_60"].notna().sum()


def test_bbands_three_bands() -> None:
    engine = IndicatorEngine()
    out = engine.calculate(_load_fixture(), "BBANDS_20")
    assert out.columns.tolist() == ["upper", "middle", "lower"]


def test_invalid_indicator_raises() -> None:
    engine = IndicatorEngine()
    with pytest.raises(ValueError, match="Unsupported indicator"):
        engine.calculate(_load_fixture(), "FOOBAR")


def test_list_supported() -> None:
    engine = IndicatorEngine()
    supported = engine.list_supported()
    assert "KD" in supported
    assert "RSI_14" in supported
    assert "MACD" in supported
    assert "BBANDS_20" in supported
    assert "MA_20" in supported


def test_calculate_batch() -> None:
    engine = IndicatorEngine()
    df = _load_fixture()
    out = engine.calculate_batch(df, ["RSI_14", "MACD", "KD"])

    expected_cols = {"RSI_14", "macd", "signal", "histogram", "K", "D"}
    assert expected_cols.issubset(set(out.columns))
    assert len(out) == len(df)

