from __future__ import annotations

import pandas as pd

from src.core.constants import TAIPEI_TZ
from src.ui.pages.backtest import (
    _build_eps_display_table,
    _build_price_features,
    _extract_trade_markers,
    _nearest_trading_indices,
)


def test_nearest_trading_indices_prefers_future_on_tie() -> None:
    trading = pd.DatetimeIndex(
        [
            pd.Timestamp("2026-01-03", tz=TAIPEI_TZ),
            pd.Timestamp("2026-01-05", tz=TAIPEI_TZ),
        ]
    )
    targets = pd.DatetimeIndex([pd.Timestamp("2026-01-04", tz=TAIPEI_TZ)])

    nearest = _nearest_trading_indices(targets, trading)

    assert nearest.tolist() == [1]


def test_build_price_features_rolling_mean_matches_expected() -> None:
    price_df = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=6, freq="D", tz=TAIPEI_TZ),
            "close": [1, 2, 3, 4, 5, 6],
        }
    )

    out = _build_price_features(price_df)

    assert pd.isna(out.loc[3, "ma5"])
    assert out.loc[4, "ma5"] == 3.0
    assert out.loc[5, "ma5"] == 4.0
    assert out["ma20"].isna().all()
    assert out["ma60"].isna().all()


def test_build_eps_display_table_partial_latest_year_no_estimation() -> None:
    eps_df = pd.DataFrame(
        {
            "year": [2025, 2025, 2024, 2024, 2024, 2024],
            "quarter": [1, 2, 1, 2, 3, 4],
            "eps": [1.2, 1.5, 0.5, 0.5, 0.5, 0.5],
        }
    )

    display = _build_eps_display_table(eps_df=eps_df, end_year=2025)

    assert not display.empty
    assert display.iloc[0]["年度"] == 2025
    assert display.iloc[0]["Q1 EPS"] == "1.20"
    assert display.iloc[0]["Q2 EPS"] == "1.50"
    assert display.iloc[0]["Q3 EPS"] == "尚無資料"
    assert display.iloc[0]["Q4 EPS"] == "尚無資料"
    assert display.iloc[0]["年度 EPS"] == "2.70"
    assert display.iloc[1]["年度"] == 2024
    assert display.iloc[1]["年度 EPS"] == "2.00"


def test_extract_trade_markers_preserves_quantity() -> None:
    trades = pd.DataFrame(
        {
            "entry_date": [pd.Timestamp("2026-01-02", tz=TAIPEI_TZ)],
            "exit_date": [pd.Timestamp("2026-01-06", tz=TAIPEI_TZ)],
            "entry_price": [100.0],
            "exit_price": [110.0],
            "quantity": [3000],
        }
    )

    buy_marks, sell_marks = _extract_trade_markers(trades=trades)

    assert buy_marks.iloc[0]["quantity"] == 3000
    assert sell_marks.iloc[0]["quantity"] == 3000
