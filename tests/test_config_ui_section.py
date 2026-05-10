import pytest
from src.core.config import clear_config_cache, get_config
from src.ui.themes import DEFAULT_THEME, get_theme


def test_config_missing_ui_section_returns_defaults(tmp_path, monkeypatch) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("system:\n  data_dir: ./data\n", encoding="utf-8")

    monkeypatch.setattr("src.core.config.get_project_root", lambda: tmp_path)
    (tmp_path / ".env").touch()

    clear_config_cache()
    config = get_config()

    assert "ui" in config
    assert isinstance(config["ui"], dict)

    # ui.theme 缺失時，get_theme 回退應為 midnight_blue
    effective_theme, _ = get_theme(config["ui"].get("theme", ""))
    assert effective_theme == DEFAULT_THEME


def test_save_ui_section_preserves_other_sections(tmp_path, monkeypatch) -> None:
    import yaml

    config_content = {
        "ai": {"enabled": False},
        "backtest": {"initial_capital": 500000.0},
        "strategies": [{"name": "MA20_MA60", "type": "moving_average_cross", "params": {"short_window": 20, "long_window": 60}}],
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config_content, allow_unicode=True), encoding="utf-8")
    (tmp_path / ".env").touch()

    monkeypatch.setattr("src.core.config.get_project_root", lambda: tmp_path)
    monkeypatch.setattr("src.ui.pages.settings.get_project_root", lambda: tmp_path)

    clear_config_cache()

    from src.ui.pages.settings import _save_non_strategy_config_and_env
    _save_non_strategy_config_and_env(
        theme="midnight_blue", use_extras=True, use_option_menu=True,
        ai_enabled=False, provider="anthropic", model="",
        max_daily_loss_pct=0.03, max_position_pct=0.20, max_drawdown_warning_pct=0.10,
        initial_capital=500000.0,
        openai_key="", anthropic_key="", gemini_key="",
    )

    saved = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    assert saved["strategies"][0]["name"] == "MA20_MA60"
    assert saved["ai"]["enabled"] == False
    assert saved["ui"]["theme"] == "midnight_blue"
