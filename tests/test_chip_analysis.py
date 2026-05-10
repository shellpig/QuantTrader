from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from src.analysis.chip_analysis import generate_chip_summary
from src.core.constants import INSTITUTIONAL_COLUMNS, MARGIN_COLUMNS
from src.data.fetcher import FinMindFetcher
from src.data.storage import ParquetStorage


@dataclass
class _DummyResponse:
    payload: dict

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self.payload


class _DummySession:
    def __init__(self, payloads: list[dict]):
        self._payloads = payloads
        self.calls: list[dict] = []

    def get(self, *args, **kwargs):  # noqa: ANN002, ANN003
        params = kwargs.get("params", {})
        self.calls.append(dict(params))
        payload = self._payloads[len(self.calls) - 1]
        return _DummyResponse(payload=payload)


def _institutional_payload() -> dict:
    return {
        "data": [
            {"date": "2026-01-01", "stock_id": "2330", "name": "Foreign_Investor", "buy": 2000, "sell": 500},
            {"date": "2026-01-01", "stock_id": "2330", "name": "Foreign_Dealer_Self", "buy": 1000, "sell": 200},
            {"date": "2026-01-01", "stock_id": "2330", "name": "Investment_Trust", "buy": 500, "sell": 200},
            {"date": "2026-01-01", "stock_id": "2330", "name": "Dealer_self", "buy": 700, "sell": 400},
            {"date": "2026-01-01", "stock_id": "2330", "name": "Dealer_Hedging", "buy": 200, "sell": 300},
            {"date": "2026-01-02", "stock_id": "2330", "name": "Foreign_Investor", "buy": 1000, "sell": 1200},
            {"date": "2026-01-02", "stock_id": "2330", "name": "Investment_Trust", "buy": 200, "sell": 800},
            {"date": "2026-01-02", "stock_id": "2330", "name": "Dealer_self", "buy": 400, "sell": 100},
        ]
    }


def _margin_payload() -> dict:
    return {
        "data": [
            {
                "date": "2026-01-01",
                "stock_id": "2330",
                "MarginPurchaseBuy": 100,
                "MarginPurchaseSell": 80,
                "MarginPurchaseTodayBalance": 5000,
                "ShortSaleBuy": 30,
                "ShortSaleSell": 35,
                "ShortSaleTodayBalance": 1200,
            },
            {
                "date": "2026-01-02",
                "stock_id": "2330",
                "MarginPurchaseBuy": 90,
                "MarginPurchaseSell": 70,
                "MarginPurchaseTodayBalance": 5020,
                "ShortSaleBuy": 20,
                "ShortSaleSell": 25,
                "ShortSaleTodayBalance": 1195,
            },
        ]
    }


def _make_institutional_df_with_signs(signs: list[int]) -> pd.DataFrame:
    rows = []
    base_date = pd.Timestamp("2026-01-01")
    for i, sign in enumerate(signs):
        rows.append(
            {
                "date": base_date + pd.Timedelta(days=i),
                "foreign_net": sign * 3000,
                "trust_net": sign * 2000,
                "dealer_net": sign * 1000,
            }
        )
    out = pd.DataFrame(rows)
    out["symbol"] = "2330"
    for col in ("foreign_buy", "foreign_sell", "trust_buy", "trust_sell", "dealer_buy", "dealer_sell"):
        out[col] = 0
    out = out[
        [
            "date",
            "foreign_buy",
            "foreign_sell",
            "foreign_net",
            "trust_buy",
            "trust_sell",
            "trust_net",
            "dealer_buy",
            "dealer_sell",
            "dealer_net",
            "symbol",
        ]
    ].copy()
    return out


def _make_margin_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "margin_buy": [100, 90, 80],
            "margin_sell": [70, 80, 75],
            "margin_balance": [5000, 5020, 5050],
            "short_buy": [20, 25, 30],
            "short_sell": [25, 20, 18],
            "short_balance": [1200, 1190, 1180],
            "symbol": ["2330", "2330", "2330"],
        }
    )


def test_fetch_institutional_returns_wide_format() -> None:
    session = _DummySession([_institutional_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    df = fetcher.fetch_institutional("2330", "2026-01-01")
    assert df.columns.tolist() == INSTITUTIONAL_COLUMNS
    assert len(df) == 2


def test_fetch_institutional_aggregates_foreign() -> None:
    session = _DummySession([_institutional_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    df = fetcher.fetch_institutional("2330", "2026-01-01")
    day1 = df[df["date"].dt.strftime("%Y-%m-%d") == "2026-01-01"].iloc[0]
    assert int(day1["foreign_buy"]) == 3000
    assert int(day1["foreign_sell"]) == 700
    assert int(day1["foreign_net"]) == 2300


def test_fetch_institutional_aggregates_dealer() -> None:
    session = _DummySession([_institutional_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    df = fetcher.fetch_institutional("2330", "2026-01-01")
    day1 = df[df["date"].dt.strftime("%Y-%m-%d") == "2026-01-01"].iloc[0]
    assert int(day1["dealer_buy"]) == 900
    assert int(day1["dealer_sell"]) == 700
    assert int(day1["dealer_net"]) == 200


def test_fetch_institutional_unit_is_shares() -> None:
    session = _DummySession([_institutional_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    df = fetcher.fetch_institutional("2330", "2026-01-01")
    day1 = df[df["date"].dt.strftime("%Y-%m-%d") == "2026-01-01"].iloc[0]
    assert int(day1["foreign_buy"]) == 3000


def test_fetch_margin_columns_correct() -> None:
    session = _DummySession([_margin_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    df = fetcher.fetch_margin("2330", "2026-01-01")
    assert df.columns.tolist() == MARGIN_COLUMNS


def test_fetch_margin_unit_is_lots() -> None:
    session = _DummySession([_margin_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    df = fetcher.fetch_margin("2330", "2026-01-01")
    day2 = df[df["date"].dt.strftime("%Y-%m-%d") == "2026-01-02"].iloc[0]
    assert int(day2["margin_balance"]) == 5020


def test_save_load_institutional_roundtrip(tmp_path) -> None:
    session = _DummySession([_institutional_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    storage = ParquetStorage(data_dir=tmp_path)
    source = fetcher.fetch_institutional("2330", "2026-01-01")
    storage.save_institutional("2330", source)
    loaded = storage.load_institutional("2330")
    pd.testing.assert_frame_equal(loaded, source)


def test_save_load_margin_roundtrip(tmp_path) -> None:
    session = _DummySession([_margin_payload()])
    fetcher = FinMindFetcher(token="dummy", session=session)
    storage = ParquetStorage(data_dir=tmp_path)
    source = fetcher.fetch_margin("2330", "2026-01-01")
    storage.save_margin("2330", source)
    loaded = storage.load_margin("2330")
    pd.testing.assert_frame_equal(loaded, source)


def test_incremental_fetch_only_missing_days(tmp_path) -> None:
    storage = ParquetStorage(data_dir=tmp_path)
    existing = pd.DataFrame(
        {
            "date": pd.date_range("2026-01-01", periods=30, freq="D", tz="Asia/Taipei"),
            "foreign_buy": [1000] * 30,
            "foreign_sell": [500] * 30,
            "foreign_net": [500] * 30,
            "trust_buy": [300] * 30,
            "trust_sell": [200] * 30,
            "trust_net": [100] * 30,
            "dealer_buy": [200] * 30,
            "dealer_sell": [150] * 30,
            "dealer_net": [50] * 30,
            "symbol": ["2330"] * 30,
        }
    )[INSTITUTIONAL_COLUMNS]
    storage.save_institutional("2330", existing)

    class _Fetcher(FinMindFetcher):
        def __init__(self):
            super().__init__(token="dummy", session=_DummySession([{"data": []}]))
            self.called_start_dates: list[str] = []

        def fetch_institutional(self, symbol: str, start_date: str) -> pd.DataFrame:
            self.called_start_dates.append(start_date)
            return pd.DataFrame(
                {
                    "date": [pd.Timestamp("2026-01-31", tz="Asia/Taipei")],
                    "foreign_buy": [1200],
                    "foreign_sell": [600],
                    "foreign_net": [600],
                    "trust_buy": [300],
                    "trust_sell": [100],
                    "trust_net": [200],
                    "dealer_buy": [250],
                    "dealer_sell": [200],
                    "dealer_net": [50],
                    "symbol": [symbol],
                }
            )[INSTITUTIONAL_COLUMNS]

    fetcher = _Fetcher()
    merged = fetcher.fetch_institutional_incremental("2330", storage, default_start_date="2020-01-01")
    assert fetcher.called_start_dates == ["2026-01-31"]
    assert len(merged) == 31


def test_chip_summary_concentrated() -> None:
    inst = _make_institutional_df_with_signs([1, 1, 1, 1, 1])
    summary = generate_chip_summary(inst, _make_margin_df(), n_days=5)
    assert summary.chip_concentration == "集中"


def test_chip_summary_dispersed() -> None:
    inst = _make_institutional_df_with_signs([-1, -1, -1, -1, -1])
    summary = generate_chip_summary(inst, _make_margin_df(), n_days=5)
    assert summary.chip_concentration == "分散"


def test_chip_summary_stable() -> None:
    inst = _make_institutional_df_with_signs([1, -1, 1, -1, 1])
    summary = generate_chip_summary(inst, _make_margin_df(), n_days=5)
    assert summary.chip_concentration == "穩定"


def test_chip_summary_label_format() -> None:
    inst = _make_institutional_df_with_signs([1, 1, 1, 1, 1])
    summary = generate_chip_summary(inst, _make_margin_df(), n_days=5)
    assert summary.foreign_label.startswith("買超 ")
    assert summary.foreign_label.endswith(" 張")


def test_chip_summary_empty_data() -> None:
    summary = generate_chip_summary(pd.DataFrame(), pd.DataFrame(), n_days=5)
    assert summary.foreign_net_n_days == 0
    assert summary.trust_net_n_days == 0
    assert summary.dealer_net_n_days == 0
    assert summary.chip_concentration == "穩定"
