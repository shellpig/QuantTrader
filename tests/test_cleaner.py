from __future__ import annotations

from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from src.data.cleaner import DataCleaner, adjust_prices, compute_adjustment_factors


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "bad_data.csv"
DIV_FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "dividends_2330.csv"


def _load_bad_data() -> pd.DataFrame:
    return pd.read_csv(FIXTURE_PATH)


def _make_adj_daily_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-06-24", "2024-06-25", "2024-06-26", "2024-06-27"]),
            "open": [99.0, 100.0, 95.0, 96.0],
            "high": [101.0, 101.0, 96.0, 97.0],
            "low": [98.0, 99.0, 94.0, 95.0],
            "close": [100.0, 100.0, 95.0, 96.0],
            "volume": [1000, 1000, 1000, 1000],
            "symbol": ["2330", "2330", "2330", "2330"],
        }
    )


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


def test_adj_factor_no_dividend() -> None:
    daily = _make_adj_daily_df()
    divs = pd.DataFrame(columns=["date", "cash_dividend", "stock_dividend", "symbol"])

    out = compute_adjustment_factors(daily, divs)

    assert "adj_factor" in out.columns
    assert (out["adj_factor"] == 1.0).all()


def test_adj_factor_cash_dividend() -> None:
    daily = _make_adj_daily_df()
    divs = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-06-26")],
            "cash_dividend": [5.0],
            "stock_dividend": [0.0],
            "symbol": ["2330"],
        }
    )

    out = compute_adjustment_factors(daily, divs)

    # Ex-date is 2024-06-26, so dates before that should have factor 0.95.
    assert out.loc[out["date"] == pd.Timestamp("2024-06-24"), "adj_factor"].iloc[0] < 1.0
    assert out.loc[out["date"] == pd.Timestamp("2024-06-25"), "adj_factor"].iloc[0] < 1.0
    assert out.loc[out["date"] == pd.Timestamp("2024-06-26"), "adj_factor"].iloc[0] == 1.0


def test_forward_adj_latest_price_unchanged() -> None:
    daily = _make_adj_daily_df()
    divs = pd.read_csv(DIV_FIXTURE_PATH)

    out = adjust_prices(daily, divs, method="forward")

    assert out.loc[out["date"] == pd.Timestamp("2024-06-27"), "close"].iloc[0] == 96.0


def test_adj_no_gap_across_ex_date() -> None:
    daily = _make_adj_daily_df()
    divs = pd.DataFrame(
        {
            "date": [pd.Timestamp("2024-06-26")],
            "cash_dividend": [5.0],
            "stock_dividend": [0.0],
            "symbol": ["2330"],
        }
    )

    out = adjust_prices(daily, divs, method="forward")

    pre_ex = out.loc[out["date"] == pd.Timestamp("2024-06-25"), "close"].iloc[0]
    ex_date = out.loc[out["date"] == pd.Timestamp("2024-06-26"), "close"].iloc[0]
    assert abs(pre_ex - ex_date) < 0.01


def test_raw_method_returns_unchanged() -> None:
    daily = _make_adj_daily_df()
    divs = pd.read_csv(DIV_FIXTURE_PATH)

    out = adjust_prices(daily, divs, method="raw")
    pdt.assert_frame_equal(out, daily)
