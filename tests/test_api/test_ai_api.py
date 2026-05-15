"""Tests for AI API endpoints — Phase 10-F-1.

Covers:
  - GET /api/ai/status  → 200 feature_locked
  - POST /api/ai/chat   → 503 AI_DISABLED (any body)
  - POST /api/ai/analyze → 503 when ai.enabled=false (regression)
  - No endpoint returns SSE in 10-F-1
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/ai/status
# ---------------------------------------------------------------------------


def test_ai_status_returns_feature_locked() -> None:
    response = client.get("/api/ai/status")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "feature_locked"
    assert "message" in body


def test_ai_status_no_sse_content_type() -> None:
    response = client.get("/api/ai/status")
    assert "text/event-stream" not in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# POST /api/ai/chat
# ---------------------------------------------------------------------------


def test_ai_chat_returns_503() -> None:
    response = client.post("/api/ai/chat", json={"messages": []})
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["error"]["code"] == "AI_DISABLED"


def test_ai_chat_503_with_any_body() -> None:
    response = client.post(
        "/api/ai/chat",
        json={"messages": [{"role": "user", "content": "2330 的 RSI？"}]},
    )
    assert response.status_code == 503


def test_ai_chat_503_with_empty_body() -> None:
    response = client.post("/api/ai/chat", json={})
    assert response.status_code == 503


def test_ai_chat_no_sse_content_type() -> None:
    response = client.post("/api/ai/chat", json={"messages": []})
    assert "text/event-stream" not in response.headers.get("content-type", "")


# ---------------------------------------------------------------------------
# POST /api/ai/analyze — regression: still returns 503 when AI disabled
# ---------------------------------------------------------------------------


def test_ai_analyze_returns_503_when_ai_disabled() -> None:
    from src.services.dashboard_service import DashboardPayload
    from src.analysis.pattern import MultiTimeframeAnalysis, TimeframeTrend
    import pandas as pd

    mtf = MultiTimeframeAnalysis(
        daily=TimeframeTrend("daily", "多頭", "強"),
        weekly=TimeframeTrend("weekly", "多頭", "強"),
        monthly=TimeframeTrend("monthly", "多頭", "強"),
    )
    dummy_payload = DashboardPayload(
        symbol="2330",
        market="tw",
        daily_df=pd.DataFrame(),
        technical=None,
        candle_patterns=[],
        chart_patterns=[],
        multi_timeframe=mtf,
        ai_enabled=False,
    )
    with patch("api.routers.ai.build_dashboard_payload", return_value=dummy_payload):
        response = client.post(
            "/api/ai/analyze",
            json={"symbol": "2330", "market": "tw"},
        )
    assert response.status_code == 503
    body = response.json()
    assert body["detail"]["error"]["code"] == "AI_DISABLED"
