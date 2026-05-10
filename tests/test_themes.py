from src.ui.themes import DEFAULT_THEME, THEMES, get_theme, render_theme_css


def test_get_theme_valid() -> None:
    name, palette = get_theme("midnight_blue")
    assert name == "midnight_blue"
    assert palette == THEMES["midnight_blue"]


def test_get_theme_legal_values() -> None:
    for theme_name in THEMES:
        name, palette = get_theme(theme_name)
        assert name == theme_name
        assert "background" in palette
        assert "primary" in palette
        assert "plotly_template" in palette


def test_get_theme_invalid_falls_back_to_midnight_blue() -> None:
    name, palette = get_theme("invalid_theme")
    assert name == "midnight_blue"
    assert palette == THEMES["midnight_blue"]


def test_get_theme_empty_falls_back_to_midnight_blue() -> None:
    name, _ = get_theme("")
    assert name == DEFAULT_THEME


def test_render_theme_css_contains_required_selectors() -> None:
    css = render_theme_css("arctic_light")
    assert "stAppViewContainer" in css
    assert "stSidebar" in css
    assert "body" in css or ":root" in css


def test_render_theme_css_hides_sidebar_nav() -> None:
    css = render_theme_css("midnight_blue")
    assert "stSidebarNav" in css
    assert "display: none" in css or "display:none" in css
