"""Rule-based technical summary for Phase 8-A dashboard."""

from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd
import pandas_ta as ta

_REQUIRED_COLUMNS = ("open", "high", "low", "close", "volume")
_DATA_INSUFFICIENT = "資料不足"


@dataclass
class PriceLevel:
    value: float
    label: str
    kind: str


@dataclass
class TechnicalSummary:
    trend_direction: str
    ma_status: str
    kd_status: str
    macd_status: str
    volume_status: str
    volume_price_relation: str
    short_term_score: float
    short_term_label: str
    short_term_components: dict[str, float]
    resistance_levels: list[PriceLevel] = field(default_factory=list)
    support_levels: list[PriceLevel] = field(default_factory=list)
    volume_price_divergence: str = ""
    ma_bias: str = ""
    chip_behavior: str = ""
    operation_observation: str = ""


def generate_technical_summary(
    df: pd.DataFrame,
    *,
    chip_behavior: str = "",
) -> TechnicalSummary:
    """Generate rule-based technical summary from daily OHLCV."""
    _validate_input(df)

    close = pd.to_numeric(df["close"], errors="coerce")
    high = pd.to_numeric(df["high"], errors="coerce")
    low = pd.to_numeric(df["low"], errors="coerce")
    volume = pd.to_numeric(df["volume"], errors="coerce")

    ma5 = close.rolling(window=5, min_periods=5).mean()
    ma20 = close.rolling(window=20, min_periods=20).mean()
    ma60 = close.rolling(window=60, min_periods=60).mean()

    latest_close = _last_value(close)
    latest_ma5 = _last_value(ma5)
    latest_ma20 = _last_value(ma20)
    latest_ma60 = _last_value(ma60)

    trend_direction = _determine_trend(latest_ma5, latest_ma20, latest_ma60)
    ma_status = _determine_ma_status(latest_ma5, latest_ma20, latest_ma60, latest_close)
    kd_status = _determine_kd_status(high, low, close)
    macd_status = _determine_macd_status(close)

    avg_5d_vol = _last_value(volume.rolling(window=5, min_periods=5).mean())
    today_vol = _last_value(volume)
    volume_status, volume_ratio = _assess_volume(today_vol, avg_5d_vol)
    volume_price_relation = _assess_volume_price_relation(close, volume_ratio)

    resistance_levels = _find_resistance_levels(high)
    support_levels = _find_support_levels(low, latest_ma20, latest_ma60, latest_close)

    ma_score = _score_ma(trend_direction, ma_status)
    kd_score = _score_kd(kd_status)
    volume_price_score = _score_volume_price(volume_price_relation)
    breakout_score = _score_breakout(latest_close, resistance_levels, support_levels)

    short_term_score, short_term_label, short_term_components = _calculate_short_term_score(
        ma_score=ma_score,
        kd_score=kd_score,
        volume_price_score=volume_price_score,
        breakout_score=breakout_score,
    )

    volume_price_divergence = _build_volume_price_divergence(volume_price_relation)
    ma_bias = _build_ma_bias(latest_close, latest_ma20)
    operation_observation = _build_operation_observation(
        trend_direction=trend_direction,
        volume_price_divergence=volume_price_divergence,
        ma_bias=ma_bias,
        chip_behavior=chip_behavior,
    )

    return TechnicalSummary(
        trend_direction=trend_direction,
        ma_status=ma_status,
        kd_status=kd_status,
        macd_status=macd_status,
        volume_status=volume_status,
        volume_price_relation=volume_price_relation,
        short_term_score=short_term_score,
        short_term_label=short_term_label,
        short_term_components=short_term_components,
        resistance_levels=resistance_levels,
        support_levels=support_levels,
        volume_price_divergence=volume_price_divergence,
        ma_bias=ma_bias,
        chip_behavior=chip_behavior,
        operation_observation=operation_observation,
    )


def _validate_input(df: pd.DataFrame) -> None:
    if not isinstance(df, pd.DataFrame) or df.empty:
        raise ValueError("df must be a non-empty DataFrame.")
    missing = [col for col in _REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"df missing required columns: {missing}")


def _last_value(series: pd.Series) -> float | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if cleaned.empty:
        return None
    return float(cleaned.iloc[-1])


def _last_two_values(series: pd.Series) -> tuple[float, float] | None:
    cleaned = pd.to_numeric(series, errors="coerce").dropna()
    if len(cleaned) < 2:
        return None
    return float(cleaned.iloc[-2]), float(cleaned.iloc[-1])


def _determine_trend(ma5: float | None, ma20: float | None, ma60: float | None) -> str:
    if ma5 is None or ma20 is None:
        return _DATA_INSUFFICIENT
    if ma60 is None:
        if ma5 > ma20:
            return "多頭趨勢"
        if ma5 < ma20:
            return "空頭趨勢"
        return "盤整"
    if ma5 > ma20 > ma60:
        return "多頭趨勢"
    if ma5 < ma20 < ma60:
        return "空頭趨勢"
    return "盤整"


def _determine_ma_status(
    ma5: float | None,
    ma20: float | None,
    ma60: float | None,
    close: float | None,
) -> str:
    if ma5 is None or ma20 is None:
        return _DATA_INSUFFICIENT
    if ma60 is None:
        return f"{_DATA_INSUFFICIENT}（MA60）"
    if ma5 > ma20 > ma60:
        return "多頭排列 (5>20>60)"
    if ma5 < ma20 < ma60:
        return "空頭排列 (5<20<60)"
    if close is None:
        return "均線糾結"
    if close >= ma20:
        return "均線糾結（偏多）"
    return "均線糾結（偏空）"


def _find_prefixed_col(columns: pd.Index, prefix: str) -> str | None:
    prefix_upper = prefix.upper()
    for col in columns:
        if str(col).upper().startswith(prefix_upper):
            return str(col)
    return None


def _determine_kd_status(high: pd.Series, low: pd.Series, close: pd.Series) -> str:
    stoch = ta.stoch(high=high, low=low, close=close, k=9, d=3, smooth_k=3)
    if stoch is None or stoch.empty:
        return _DATA_INSUFFICIENT

    k_col = _find_prefixed_col(stoch.columns, "STOCHK_")
    d_col = _find_prefixed_col(stoch.columns, "STOCHD_")
    if k_col is None or d_col is None:
        return _DATA_INSUFFICIENT

    k_vals = pd.to_numeric(stoch[k_col], errors="coerce")
    d_vals = pd.to_numeric(stoch[d_col], errors="coerce")
    latest = _last_value(k_vals), _last_value(d_vals)
    if latest[0] is None or latest[1] is None:
        return _DATA_INSUFFICIENT

    k_curr, d_curr = latest
    prev_pair = _last_two_values(k_vals), _last_two_values(d_vals)
    has_prev = prev_pair[0] is not None and prev_pair[1] is not None
    if k_curr > 80 and d_curr > 80:
        return "KD 高檔鈍化"
    if k_curr < 20 and d_curr < 20:
        return "KD 低檔鈍化"
    if has_prev:
        k_prev = prev_pair[0][0]  # type: ignore[index]
        d_prev = prev_pair[1][0]  # type: ignore[index]
        if k_prev <= d_prev and k_curr > d_curr:
            return "KD 黃金交叉"
        if k_prev >= d_prev and k_curr < d_curr:
            return "KD 死亡交叉"
    if k_curr > d_curr:
        return "KD 多方"
    return "KD 空方"


def _determine_macd_status(close: pd.Series) -> str:
    macd_df = ta.macd(close, fast=12, slow=26, signal=9)
    if macd_df is None or macd_df.empty:
        return _DATA_INSUFFICIENT

    dif_col = _find_prefixed_col(macd_df.columns, "MACD_")
    dea_col = _find_prefixed_col(macd_df.columns, "MACDS_")
    if dif_col is None or dea_col is None:
        return _DATA_INSUFFICIENT

    dif = _last_value(macd_df[dif_col])
    dea = _last_value(macd_df[dea_col])
    if dif is None or dea is None:
        return _DATA_INSUFFICIENT
    if dif > 0 and dif > dea:
        return "正值擴張"
    if dif > 0 and dif <= dea:
        return "正值收斂"
    if dif < 0 and dif < dea:
        return "負值擴張"
    if dif < 0 and dif >= dea:
        return "負值收斂"
    return "零軸附近震盪"


def _assess_volume(today_vol: float | None, avg_5d_vol: float | None) -> tuple[str, float | None]:
    if today_vol is None or avg_5d_vol is None or avg_5d_vol <= 0:
        return _DATA_INSUFFICIENT, None
    ratio = today_vol / avg_5d_vol
    if ratio > 1.5:
        if ratio >= 3.0:
            return "爆量", ratio
        return "量能放大", ratio
    if ratio < 0.7:
        return "量能略縮", ratio
    return "量能正常", ratio


def _assess_volume_price_relation(close: pd.Series, volume_ratio: float | None) -> str:
    close_pair = _last_two_values(close)
    if close_pair is None or volume_ratio is None:
        return _DATA_INSUFFICIENT

    prev_close, curr_close = close_pair
    if curr_close > prev_close:
        if volume_ratio >= 1.0:
            return "價漲量增"
        return "價漲量縮（短線整理）"
    if curr_close < prev_close:
        if volume_ratio >= 1.0:
            return "價跌量增"
        return "價跌量縮"
    return "量價同步"


def _unique_levels(levels: list[PriceLevel]) -> list[PriceLevel]:
    seen: set[tuple[str, int]] = set()
    out: list[PriceLevel] = []
    for level in levels:
        key = (level.kind, int(round(level.value * 10000)))
        if key in seen:
            continue
        seen.add(key)
        out.append(level)
    return out


def _find_resistance_levels(high: pd.Series) -> list[PriceLevel]:
    h = pd.to_numeric(high, errors="coerce")
    if h.dropna().empty:
        return []

    levels: list[PriceLevel] = []
    high_60 = _last_value(h.tail(60))
    high_20 = _last_value(h.tail(20))

    if high_60 is not None:
        levels.append(PriceLevel(value=high_60, label="近60日高點", kind="resistance"))
    if high_20 is not None and high_60 is not None:
        tolerance = max(abs(high_60) * 0.005, 0.01)
        if abs(high_20 - high_60) > tolerance:
            levels.append(PriceLevel(value=high_20, label="近20日高點", kind="resistance"))

    return _unique_levels(levels)[:2]


def _find_support_levels(
    low: pd.Series,
    ma20: float | None,
    ma60: float | None,
    close: float | None,
) -> list[PriceLevel]:
    l = pd.to_numeric(low, errors="coerce")
    levels: list[PriceLevel] = []

    low_20 = _last_value(l.tail(20))
    if low_20 is not None:
        levels.append(PriceLevel(value=low_20, label="近期低點", kind="support"))
    if ma20 is not None:
        levels.append(PriceLevel(value=ma20, label="MA20", kind="support"))
    if ma60 is not None:
        levels.append(PriceLevel(value=ma60, label="MA60", kind="support"))

    unique_levels = _unique_levels(levels)
    if close is None:
        return unique_levels[:3]
    sorted_levels = sorted(unique_levels, key=lambda level: abs(level.value - close))
    return sorted_levels[:3]


def _score_ma(trend_direction: str, ma_status: str) -> float:
    if _DATA_INSUFFICIENT in ma_status or trend_direction == _DATA_INSUFFICIENT:
        return 0.5
    if trend_direction == "多頭趨勢":
        return 1.0
    if trend_direction == "空頭趨勢":
        return 0.0
    return 0.5


def _score_kd(kd_status: str) -> float:
    mapping = {
        "KD 黃金交叉": 0.85,
        "KD 高檔鈍化": 0.75,
        "KD 多方": 0.65,
        "KD 低檔鈍化": 0.55,
        "KD 空方": 0.35,
        "KD 死亡交叉": 0.2,
    }
    return mapping.get(kd_status, 0.5)


def _score_volume_price(volume_price_relation: str) -> float:
    mapping = {
        "價漲量增": 0.8,
        "價漲量縮（短線整理）": 0.55,
        "量價同步": 0.6,
        "價跌量縮": 0.4,
        "價跌量增": 0.2,
    }
    return mapping.get(volume_price_relation, 0.5)


def _score_breakout(
    close: float | None,
    resistance_levels: list[PriceLevel],
    support_levels: list[PriceLevel],
) -> float:
    if close is None:
        return 0.5

    resistance_values = [level.value for level in resistance_levels]
    support_values = [level.value for level in support_levels]

    if resistance_values and close > max(resistance_values):
        return 1.0
    if support_values and close < min(support_values):
        return 0.2
    if resistance_values and close >= max(resistance_values) * 0.98:
        return 0.7
    if support_values and close <= min(support_values) * 1.02:
        return 0.45
    return 0.5


def _calculate_short_term_score(
    *,
    ma_score: float,
    kd_score: float,
    volume_price_score: float,
    breakout_score: float,
) -> tuple[float, str, dict[str, float]]:
    score = (
        ma_score * 0.30
        + kd_score * 0.25
        + volume_price_score * 0.25
        + breakout_score * 0.20
    )
    score = max(0.0, min(1.0, score))

    if score >= 0.7:
        label = "強勢偏多"
    elif score >= 0.5:
        label = "中等偏多"
    elif score >= 0.3:
        label = "中性"
    else:
        label = "偏空"

    components = {
        "ma": round(ma_score, 4),
        "kd": round(kd_score, 4),
        "volume_price": round(volume_price_score, 4),
        "breakout": round(breakout_score, 4),
    }
    return round(score, 4), label, components


def _build_volume_price_divergence(volume_price_relation: str) -> str:
    if volume_price_relation in {"價漲量縮（短線整理）", "價跌量縮"}:
        return f"量價背離：{volume_price_relation}"
    if volume_price_relation == _DATA_INSUFFICIENT:
        return _DATA_INSUFFICIENT
    return "量價同步"


def _build_ma_bias(close: float | None, ma20: float | None) -> str:
    if close is None or ma20 is None or ma20 == 0:
        return _DATA_INSUFFICIENT
    bias = (close - ma20) / ma20 * 100
    if bias > 3:
        tone = "偏高"
    elif bias < -3:
        tone = "偏低"
    else:
        tone = "中性"
    return f"與 MA20 乖離約 {bias:+.2f}%，{tone}"


def _build_operation_observation(
    *,
    trend_direction: str,
    volume_price_divergence: str,
    ma_bias: str,
    chip_behavior: str,
) -> str:
    parts = [f"目前趨勢：{trend_direction}。"]
    if volume_price_divergence and volume_price_divergence != _DATA_INSUFFICIENT:
        parts.append(f"{volume_price_divergence}。")
    if ma_bias and ma_bias != _DATA_INSUFFICIENT:
        parts.append(f"{ma_bias}。")
    if chip_behavior:
        parts.append(f"籌碼觀察：{chip_behavior}。")
    if len(parts) == 1:
        parts.append("關鍵欄位資料不足。")
    return "".join(parts)
