"""Unit tests for settings page helper functions (Phase 6-B)."""

from __future__ import annotations

import yaml
import pytest

from src.core.config import clear_config_cache


@pytest.fixture()
def config_dir(tmp_path, monkeypatch):
    """Provide a temp dir with a two-strategy config and monkeypatched project root."""
    config = {
        "strategies": [
            {"name": "MA20_MA60", "type": "moving_average_cross", "params": {"short_window": 20, "long_window": 60}},
            {"name": "RSI_14", "type": "rsi", "params": {"period": 14, "oversold": 30.0, "overbought": 70.0}},
        ],
        "ui": {"theme": "arctic_light", "use_extras": True, "use_option_menu": True},
        "ai": {"enabled": False, "provider": "anthropic", "model": ""},
        "risk": {"max_daily_loss_pct": 0.03, "max_position_pct": 0.20, "max_drawdown_warning_pct": 0.10},
        "backtest": {"initial_capital": 1_000_000.0},
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, allow_unicode=True), encoding="utf-8")
    (tmp_path / ".env").touch()

    monkeypatch.setattr("src.core.config.get_project_root", lambda: tmp_path)
    monkeypatch.setattr("src.ui.pages.settings.get_project_root", lambda: tmp_path)
    clear_config_cache()
    return tmp_path


def test_save_non_strategy_config_preserves_strategies(config_dir) -> None:
    from src.ui.pages.settings import _save_non_strategy_config_and_env

    _save_non_strategy_config_and_env(
        theme="midnight_blue", use_extras=True, use_option_menu=True,
        ai_enabled=True, provider="anthropic", model="claude-opus-4-7",
        max_daily_loss_pct=0.05, max_position_pct=0.25, max_drawdown_warning_pct=0.15,
        initial_capital=2_000_000.0,
        openai_key="", anthropic_key="sk-test", gemini_key="",
    )
    saved = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))

    # strategies[] must be untouched
    assert len(saved["strategies"]) == 2
    assert saved["strategies"][0]["name"] == "MA20_MA60"
    assert saved["strategies"][1]["name"] == "RSI_14"

    # ui and ai should be updated
    assert saved["ui"]["theme"] == "midnight_blue"
    assert saved["ai"]["enabled"] is True
    assert saved["backtest"]["initial_capital"] == 2_000_000.0


def test_save_strategy_presets_preserves_non_strategy_sections(config_dir) -> None:
    from src.ui.pages.settings import _save_strategy_presets
    clear_config_cache()

    new_strategies = [
        {"name": "KD_Cross", "type": "kd_cross", "params": {"k_period": 9, "d_period": 3, "smooth_k": 3}},
    ]
    _save_strategy_presets(new_strategies)

    saved = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))

    # strategies[] updated
    assert len(saved["strategies"]) == 1
    assert saved["strategies"][0]["name"] == "KD_Cross"

    # non-strategy sections must be untouched
    assert saved["ui"]["theme"] == "arctic_light"
    assert saved["ai"]["enabled"] is False
    assert saved["backtest"]["initial_capital"] == 1_000_000.0


def test_delete_strategy_preset_removes_only_one(config_dir) -> None:
    from src.ui.pages.settings import _delete_strategy_preset
    clear_config_cache()

    _delete_strategy_preset("MA20_MA60")

    saved = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
    names = [p["name"] for p in saved["strategies"]]

    assert "MA20_MA60" not in names
    assert "RSI_14" in names
    assert len(names) == 1

    # non-strategy sections still intact
    assert saved["ui"]["theme"] == "arctic_light"
    assert saved["backtest"]["initial_capital"] == 1_000_000.0


def test_delete_nonexistent_preset_is_no_op(config_dir) -> None:
    from src.ui.pages.settings import _delete_strategy_preset
    clear_config_cache()

    _delete_strategy_preset("DoesNotExist")

    saved = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
    assert len(saved["strategies"]) == 2


def test_restore_strategy_defaults_writes_8_presets(config_dir) -> None:
    from src.ui.pages.settings import _restore_strategy_defaults
    from src.core.strategy_config import STRATEGY_META
    clear_config_cache()

    _restore_strategy_defaults()

    saved = yaml.safe_load((config_dir / "config.yaml").read_text(encoding="utf-8"))
    types = {p["type"] for p in saved["strategies"]}
    assert types == set(STRATEGY_META.keys())

    # non-strategy sections still intact
    assert saved["ui"]["theme"] == "arctic_light"
