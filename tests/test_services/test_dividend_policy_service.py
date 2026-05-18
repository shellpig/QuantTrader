"""Tests for src/services/dividend_policy_service.py (Phase 11-D)."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.services.dividend_policy_service import (
    _load_cache,
    extract_goodinfo_dividend_policy_from_html,
    fetch_goodinfo_dividend_policy_html,
    get_goodinfo_dividend_policy,
)

FIXTURE_HTML = (Path(__file__).parent.parent / "fixtures" / "goodinfo_dividend_policy_sample.html").read_text(
    encoding="utf-8"
)

TODAY_2026 = pd.Timestamp("2026-05-18", tz="Asia/Taipei")


# ---------------------------------------------------------------------------
# Parser tests (11-D-P1 ~ 11-D-P5)
# ---------------------------------------------------------------------------


def test_parser_extracts_year_cash_stock(tmp_path: Path) -> None:
    """11-D-P1: fixture HTML parses year, cash_dividend, stock_dividend."""
    df = extract_goodinfo_dividend_policy_from_html(FIXTURE_HTML)
    assert not df.empty
    assert set(df.columns) >= {"year", "cash_dividend", "stock_dividend"}
    assert 2026 in df["year"].values
    row = df[df["year"] == 2026].iloc[0]
    assert row["cash_dividend"] == pytest.approx(32.0)
    assert row["stock_dividend"] == pytest.approx(10.0)


def test_parser_multiindex_columns() -> None:
    """11-D-P2: MultiIndex columns are flattened, keywords still found."""
    html = """
    <table>
      <thead>
        <tr><th colspan="2">股利資訊</th></tr>
        <tr><th>股利發放期間</th><th>現金股利(元)</th><th>股票股利(元)</th></tr>
      </thead>
      <tbody>
        <tr><td>2025年</td><td>20.00</td><td>0.00</td></tr>
      </tbody>
    </table>
    """
    df = extract_goodinfo_dividend_policy_from_html(html)
    assert not df.empty
    assert 2025 in df["year"].values


def test_parser_normalizes_dashes_and_commas() -> None:
    """11-D-P3: dashes treated as null, comma numbers normalized."""
    html = """
    <table>
      <thead>
        <tr><th>股利發放期間</th><th>現金股利</th><th>股票股利</th></tr>
      </thead>
      <tbody>
        <tr><td>2024年</td><td>1,234.50</td><td>--</td></tr>
        <tr><td>2023年</td><td>-</td><td>5.00</td></tr>
      </tbody>
    </table>
    """
    df = extract_goodinfo_dividend_policy_from_html(html)
    assert 2024 in df["year"].values
    row_2024 = df[df["year"] == 2024].iloc[0]
    assert row_2024["cash_dividend"] == pytest.approx(1234.5)
    assert pd.isna(row_2024["stock_dividend"])
    row_2023 = df[df["year"] == 2023].iloc[0]
    assert pd.isna(row_2023["cash_dividend"])
    assert row_2023["stock_dividend"] == pytest.approx(5.0)


def test_parser_deduplicates_by_year_keeps_last() -> None:
    """11-D-P4: multiple tables merged, deduplicated by year, latest kept."""
    html = """
    <table>
      <thead><tr><th>股利發放期間</th><th>現金股利</th><th>股票股利</th></tr></thead>
      <tbody>
        <tr><td>2025年</td><td>10.00</td><td>0.00</td></tr>
      </tbody>
    </table>
    <table>
      <thead><tr><th>股利發放期間</th><th>現金股利</th><th>股票股利</th></tr></thead>
      <tbody>
        <tr><td>2025年</td><td>20.00</td><td>5.00</td></tr>
        <tr><td>2026年</td><td>30.00</td><td>0.00</td></tr>
      </tbody>
    </table>
    """
    df = extract_goodinfo_dividend_policy_from_html(html)
    assert df["year"].value_counts().max() == 1  # no duplicates
    row_2025 = df[df["year"] == 2025].iloc[0]
    # last occurrence wins
    assert row_2025["cash_dividend"] == pytest.approx(20.0)


def test_parser_no_matching_table_returns_empty() -> None:
    """11-D-P5: HTML with no dividend table returns empty DataFrame."""
    html = "<html><body><table><tr><th>標題</th><td>值</td></tr></table></body></html>"
    df = extract_goodinfo_dividend_policy_from_html(html)
    assert df.empty


def test_service_selects_oldest_undetermined_goodinfo_period_2330() -> None:
    """Goodinfo detail rows: choose older unpaid period, not year total or newest unpaid period."""
    html = """
    <table>
      <thead>
        <tr>
          <th rowspan="3">股利發放期間</th>
          <th rowspan="3">股利所屬期間</th>
          <th colspan="6">股東股利 (元/股)</th>
        </tr>
        <tr>
          <th colspan="3">現金股利</th>
          <th colspan="3">股票股利</th>
        </tr>
        <tr>
          <th>盈餘</th><th>公積</th><th>合計</th>
          <th>盈餘</th><th>公積</th><th>合計</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>2026</td><td>-</td><td>19</td><td>0</td><td>19</td><td>0</td><td>0</td><td>0</td></tr>
        <tr><td>未定</td><td>26Q1</td><td>7</td><td>0</td><td>7</td><td>0</td><td>0</td><td>0</td></tr>
        <tr><td>未定</td><td>25Q4</td><td>6</td><td>0</td><td>6</td><td>0</td><td>0</td><td>0</td></tr>
        <tr><td>3/17</td><td>25Q3</td><td>6</td><td>0</td><td>6</td><td>0</td><td>0</td><td>0</td></tr>
      </tbody>
    </table>
    """
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            return_value=html,
        ),
    ):
        result = get_goodinfo_dividend_policy("2330", today=TODAY_2026)

    assert result["status"] == "current_year"
    assert result["year"] == 2026
    assert result["period"] == "25Q4"
    assert result["payment_status"] == "undetermined"
    assert result["cash_dividend"] == pytest.approx(6.0)
    assert result["stock_dividend"] == pytest.approx(0.0)


def test_service_selects_undetermined_goodinfo_half_year_period_3293() -> None:
    html = """
    <table>
      <thead>
        <tr>
          <th rowspan="3">股利發放期間</th>
          <th rowspan="3">股利所屬期間</th>
          <th colspan="6">股東股利 (元/股)</th>
        </tr>
        <tr>
          <th colspan="3">現金股利</th>
          <th colspan="3">股票股利</th>
        </tr>
        <tr>
          <th>盈餘</th><th>公積</th><th>合計</th>
          <th>盈餘</th><th>公積</th><th>合計</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>2026</td><td>-</td><td>36</td><td>0</td><td>36</td><td>0</td><td>0</td><td>0</td></tr>
        <tr><td>未定</td><td>25H2</td><td>36</td><td>0</td><td>36</td><td>0</td><td>0</td><td>0</td></tr>
        <tr><td>無</td><td>25H1</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td><td>0</td></tr>
      </tbody>
    </table>
    """
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            return_value=html,
        ),
    ):
        result = get_goodinfo_dividend_policy("3293", today=TODAY_2026)

    assert result["status"] == "current_year"
    assert result["year"] == 2026
    assert result["period"] == "25H2"
    assert result["payment_status"] == "undetermined"
    assert result["cash_dividend"] == pytest.approx(36.0)
    assert result["stock_dividend"] == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# Service tests (11-D-S1 ~ 11-D-S7)
# ---------------------------------------------------------------------------


def _make_service_mocks(has_cache: bool = False, cached_payload: dict | None = None):
    """Helper returning (mock_load_cache, mock_save_cache, mock_fetch)."""
    mock_load = MagicMock(return_value=cached_payload if has_cache else None)
    mock_save = MagicMock()
    return mock_load, mock_save


def test_service_current_year_status(tmp_path: Path) -> None:
    """11-D-S3: latest Goodinfo year == today's year → status current_year."""
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            return_value=FIXTURE_HTML,
        ),
    ):
        result = get_goodinfo_dividend_policy("3293", today=TODAY_2026)

    assert result["status"] == "current_year"
    assert result["year"] == 2026
    assert result["cash_dividend"] == pytest.approx(32.0)
    assert result["stock_dividend"] == pytest.approx(10.0)
    assert "goodinfo.tw" in result["source_url"]
    assert result["source_note"] != ""


def test_service_stale_when_latest_year_past(tmp_path: Path) -> None:
    """11-D-S4: latest Goodinfo year < today's year → status stale."""
    html_2025 = """
    <table>
      <thead><tr><th>股利發放期間</th><th>現金股利</th><th>股票股利</th></tr></thead>
      <tbody><tr><td>2025年</td><td>15.00</td><td>0.00</td></tr></tbody>
    </table>
    """
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            return_value=html_2025,
        ),
    ):
        result = get_goodinfo_dividend_policy("2330", today=TODAY_2026)

    assert result["status"] == "stale"
    assert result["year"] == 2025


def test_service_fetch_failed_returns_200_compatible_status() -> None:
    """11-D-S5: fetch/Playwright failure → status fetch_failed, no exception raised."""
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            side_effect=RuntimeError("playwright not installed"),
        ),
    ):
        result = get_goodinfo_dividend_policy("2330", today=TODAY_2026)

    assert result["status"] == "fetch_failed"
    assert "goodinfo.tw" in result["source_url"]


def test_service_stock_dividend_defaults_to_zero_when_absent() -> None:
    """11-D-S6: stock_dividend missing → fallback 0.0."""
    html_no_stock = """
    <table>
      <thead><tr><th>股利發放期間</th><th>現金股利</th></tr></thead>
      <tbody><tr><td>2026年</td><td>20.00</td></tr></tbody>
    </table>
    """
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            return_value=html_no_stock,
        ),
    ):
        result = get_goodinfo_dividend_policy("2330", today=TODAY_2026)

    assert result["status"] == "current_year"
    assert result["stock_dividend"] == pytest.approx(0.0)


def test_service_cache_hit_skips_fetch() -> None:
    """11-D-S7: cache hit → fetch is never called."""
    cached = {
        "status": "current_year",
        "year": 2026,
        "cash_dividend": 29.0,
        "stock_dividend": 0.0,
        "source_url": "https://goodinfo.tw/tw/StockDividendPolicy.asp?STOCK_ID=3293",
        "source_note": "此為網頁抓取資料，請自行前往來源確認",
    }
    mock_fetch = MagicMock()
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=cached),
        patch("src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html", mock_fetch),
    ):
        result = get_goodinfo_dividend_policy("3293", today=TODAY_2026)

    mock_fetch.assert_not_called()
    assert result["year"] == 2026


def test_service_not_found_when_no_table() -> None:
    """11-D-P5 via service: empty parse → not_found status."""
    html_empty = "<html><body><p>no table here</p></body></html>"
    with (
        patch("src.services.dividend_policy_service._load_cache", return_value=None),
        patch("src.services.dividend_policy_service._save_cache"),
        patch(
            "src.services.dividend_policy_service.fetch_goodinfo_dividend_policy_html",
            return_value=html_empty,
        ),
    ):
        result = get_goodinfo_dividend_policy("9999", today=TODAY_2026)

    assert result["status"] == "not_found"


def test_legacy_cache_without_schema_version_is_ignored(tmp_path: Path) -> None:
    """Old fetch_failed/not_found cache must not hide parser/fetcher fixes forever."""
    cache_dir = tmp_path / "cache" / "goodinfo_dividend_policy"
    cache_dir.mkdir(parents=True)
    (cache_dir / "2330_2026-05-18.json").write_text(
        json.dumps(
            {
                "status": "fetch_failed",
                "year": None,
                "cash_dividend": None,
                "stock_dividend": None,
                "source_url": "https://goodinfo.tw/tw/StockDividendPolicy.asp?STOCK_ID=2330",
                "source_note": "此為網頁抓取資料，請自行前往來源確認",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    with patch("src.services.dividend_policy_service.get_data_dir", return_value=tmp_path):
        assert _load_cache("2330", TODAY_2026) is None


def test_fetch_html_uses_requests_before_playwright() -> None:
    """Goodinfo static HTML can be fetched without requiring Playwright in the venv."""
    response = MagicMock()
    response.text = "<html><table><tr><th>股利發放期間</th></tr></table></html>"
    response.apparent_encoding = "utf-8"
    response.raise_for_status.return_value = None
    session = MagicMock()
    session.get.return_value = response

    with patch("src.services.dividend_policy_service.requests.Session", return_value=session):
        html = fetch_goodinfo_dividend_policy_html("2330")

    assert "股利發放期間" in html
    session.get.assert_called_once()


def test_fetch_html_handles_goodinfo_client_key_reinit() -> None:
    init_response = MagicMock()
    init_response.text = """
    <script>
    arr[0] = '4.8'; arr[1] = '38079.6787363216'; arr[2] = '46968.5676252104';
    window.location.replace('StockDividendPolicy.asp?STOCK_ID=2330&REINIT=46160.4868171296');
    </script>
    """
    init_response.apparent_encoding = "utf-8"
    init_response.raise_for_status.return_value = None

    table_response = MagicMock()
    table_response.text = "<html><table><tr><th>股利發放期間</th><th>現金股利</th></tr></table></html>"
    table_response.apparent_encoding = "utf-8"
    table_response.raise_for_status.return_value = None

    session = MagicMock()
    session.get.side_effect = [init_response, table_response]

    with patch("src.services.dividend_policy_service.requests.Session", return_value=session):
        html = fetch_goodinfo_dividend_policy_html("2330")

    assert "股利發放期間" in html
    assert session.get.call_count == 2
    assert "REINIT=46160.4868171296" in session.get.call_args_list[1].args[0]
    session.cookies.set.assert_called_once()
