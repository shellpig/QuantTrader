from src.ui.themes import get_theme, THEMES

def test_get_theme_valid():
    name, palette = get_theme("midnight_blue")
    assert name == "midnight_blue"
    assert palette == THEMES["midnight_blue"]

def test_get_theme_invalid_fallback_to_arctic_light():
    name, palette = get_theme("invalid_theme")
    assert name == "arctic_light"
    assert palette == THEMES["arctic_light"]
