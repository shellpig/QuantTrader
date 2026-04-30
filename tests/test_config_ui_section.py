import pytest
from src.core.config import get_config, clear_config_cache

def test_missing_ui_section(tmp_path, monkeypatch):
    config_path = tmp_path / "config.yaml"
    config_path.write_text("system:\n  data_dir: ./data\n", encoding="utf-8")
    
    # Mock get_project_root to return tmp_path
    monkeypatch.setattr("src.core.config.get_project_root", lambda: tmp_path)
    (tmp_path / ".env").touch()
    
    clear_config_cache()
    config = get_config()
    assert "ui" in config
    assert isinstance(config["ui"], dict)
    assert len(config["ui"]) == 0
