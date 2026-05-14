"""Dump a real dashboard payload for 2330 as JSON (Phase 10 mock fixture).

Usage (from repo root):
    .venv/Scripts/python.exe scripts/dump_dashboard_payload_example.py

Writes ``docs/mock_dashboard_payload.json``.

AI is read from ``config.yaml`` (default disabled), so ``analysis`` is null.
``daily_df`` is trimmed to the last 120 bars to keep the fixture small.
"""

from __future__ import annotations

import json
import sys
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import pandas as pd

from src.services.dashboard_service import (
    DashboardError,
    DashboardPayload,
    build_dashboard_payload,
)


DAILY_TAIL_BARS = 120
OUT_PATH = Path("docs/mock_dashboard_payload.json")


def _df_to_records(df: pd.DataFrame, *, tail: int | None = None) -> list[dict[str, Any]]:
    if df is None or df.empty:
        return []
    work = df.tail(tail) if tail else df
    records = work.to_dict(orient="records")
    return [{k: _jsonify(v) for k, v in row.items()} for row in records]


def _jsonify(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, pd.DataFrame):
        return _df_to_records(value)
    if is_dataclass(value):
        return {k: _jsonify(v) for k, v in asdict(value).items()}
    if isinstance(value, dict):
        return {k: _jsonify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonify(v) for v in value]
    return str(value)


def payload_to_dict(payload: DashboardPayload) -> dict[str, Any]:
    return {
        "symbol": payload.symbol,
        "market": payload.market,
        "subject_name": payload.subject_name,
        "analysis_time": payload.analysis_time,
        "ai_enabled": payload.ai_enabled,
        "daily_df": _df_to_records(payload.daily_df, tail=DAILY_TAIL_BARS),
        "technical": _jsonify(payload.technical),
        "candle_patterns": [_jsonify(p) for p in payload.candle_patterns],
        "chart_patterns": [_jsonify(p) for p in payload.chart_patterns],
        "multi_timeframe": _jsonify(payload.multi_timeframe),
        "quote": _jsonify(payload.quote),
        "bid_ask": _jsonify(payload.bid_ask),
        "chip": _jsonify(payload.chip),
        "chip_recent_df": _df_to_records(payload.chip_recent_df),
        "chip_error": payload.chip_error,
        "intraday_df": _df_to_records(payload.intraday_df),
        "intraday_snapshot": _jsonify(payload.intraday_snapshot),
        "intraday_error": payload.intraday_error,
        "analysis": _jsonify(payload.analysis),
    }


def main() -> int:
    result = build_dashboard_payload("2330", market="tw")
    if isinstance(result, DashboardError):
        print(f"[ERROR] {result.code}: {result.message}")
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    data = payload_to_dict(result)
    OUT_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    size_kb = OUT_PATH.stat().st_size / 1024
    print(f"Wrote {OUT_PATH} ({size_kb:.1f} KB)")
    print(f"  daily_df rows: {len(data['daily_df'])}")
    print(f"  chip_recent_df rows: {len(data['chip_recent_df'])}")
    print(f"  ai_enabled: {data['ai_enabled']}")
    print(f"  quote: {'present' if data['quote'] else 'null'}")
    print(f"  bid_ask: {'present' if data['bid_ask'] else 'null'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
