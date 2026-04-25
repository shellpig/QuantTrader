from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from src.data.cleaner import DataCleaner


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "bad_data.csv"


def _load_bad_data() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_PATH)


def test_l1_negative_price_removed() -> None:
    cleaner = DataCleaner()
    raw = _load_bad_data()

    cleaned, report = cleaner.clean(raw, symbol="TEST")

    assert report.negative_price_count >= 1
    assert len(cleaned) < len(raw)
    assert not (cleaned[["open", "high", "low", "close"]] < 0).any().any()


def test_l1_extreme_change_flagged() -> None:
    cleaner = DataCleaner()
    df = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [100.0, 114.0, 115.0],
            "high": [101.0, 116.0, 116.0],
            "low": [99.0, 113.0, 114.0],
            "close": [100.0, 115.0, 116.0],
            "volume": [1000, 1000, 1000],
            "symbol": ["TEST", "TEST", "TEST"],
        }
    )

    _, report = cleaner.clean(df, symbol="TEST")

    assert report.extreme_change_count >= 1
    assert "2024-01-03" in report.extreme_change_dates


def test_l1_normal_limit_up_not_flagged() -> None:
    cleaner = DataCleaner()
    df = pd.DataFrame(
        {
            "date": ["2024-01-02", "2024-01-03", "2024-01-04"],
            "open": [100.0, 109.0, 120.0],
            "high": [101.0, 111.0, 122.0],
            "low": [99.0, 108.0, 119.0],
            "close": [100.0, 110.0, 121.0],
            "volume": [1000, 1000, 1000],
            "symbol": ["TEST", "TEST", "TEST"],
        }
    )

    _, report = cleaner.clean(df, symbol="TEST")

    assert "2024-01-03" not in report.extreme_change_dates
    assert "2024-01-04" not in report.extreme_change_dates
    assert report.extreme_change_count == 0


def test_l2_ffill_3_day_gap() -> None:
    cleaner = DataCleaner()
    raw = _load_bad_data()
    cleaned, report = cleaner.clean(raw, symbol="TEST")

    assert report.filled_count >= 3

    row_0109 = cleaned.loc[cleaned["date"] == pd.Timestamp("2024-01-09"), "close"].iloc[0]
    for day in ["2024-01-10", "2024-01-11", "2024-01-12"]:
        val = cleaned.loc[cleaned["date"] == pd.Timestamp(day), "close"].iloc[0]
        assert val == row_0109


def test_l2_suspension_detected() -> None:
    cleaner = DataCleaner()
    raw = _load_bad_data()

    _, report = cleaner.clean(raw, symbol="TEST")

    assert ("2024-01-22", "2024-01-29") in report.suspension_ranges


def test_clean_returns_new_dataframe() -> None:
    cleaner = DataCleaner()
    raw = _load_bad_data()
    raw_snapshot = raw.copy(deep=True)

    cleaned, _ = cleaner.clean(raw, symbol="TEST")

    assert cleaned is not raw
    pdt.assert_frame_equal(raw, raw_snapshot)
