"""Chip analysis summary for Phase 8-C."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ChipSummary:
    foreign_net_n_days: int
    trust_net_n_days: int
    dealer_net_n_days: int
    foreign_label: str
    trust_label: str
    dealer_label: str
    chip_concentration: str
    chip_trend: str
    chip_description: str
    margin_balance_change: int
    short_balance_change: int


def generate_chip_summary(
    institutional_df: pd.DataFrame,
    margin_df: pd.DataFrame,
    *,
    n_days: int = 5,
) -> ChipSummary:
    """Generate chip summary from institutional and margin datasets."""
    n_days = max(1, int(n_days))

    inst = _prepare_institutional(institutional_df).tail(n_days)
    margin = _prepare_margin(margin_df).tail(n_days)

    foreign_net = _shares_to_lots(inst["foreign_net"].sum()) if not inst.empty else 0
    trust_net = _shares_to_lots(inst["trust_net"].sum()) if not inst.empty else 0
    dealer_net = _shares_to_lots(inst["dealer_net"].sum()) if not inst.empty else 0

    daily_total_sign = pd.Series(dtype="int64")
    if not inst.empty:
        daily_total_net = inst["foreign_net"] + inst["trust_net"] + inst["dealer_net"]
        daily_total_sign = daily_total_net.map(_sign_int).astype("int64")

    concentration = _determine_concentration(daily_total_sign)
    total_lots = foreign_net + trust_net + dealer_net
    if total_lots > 0:
        trend = "中性偏多"
    elif total_lots < 0:
        trend = "偏空"
    else:
        trend = "中性"

    if concentration == "集中":
        description = "法人同向買盤延續，籌碼集中度升高。"
    elif concentration == "分散":
        description = "法人同向偏賣，籌碼呈分散或轉弱。"
    else:
        description = "法人進出互見，籌碼趨於穩定。"

    margin_balance_change = 0
    short_balance_change = 0
    if not margin.empty:
        margin_balance_change = int(margin["margin_balance"].iloc[-1] - margin["margin_balance"].iloc[0])
        short_balance_change = int(margin["short_balance"].iloc[-1] - margin["short_balance"].iloc[0])

    return ChipSummary(
        foreign_net_n_days=foreign_net,
        trust_net_n_days=trust_net,
        dealer_net_n_days=dealer_net,
        foreign_label=_format_net_label(foreign_net),
        trust_label=_format_net_label(trust_net),
        dealer_label=_format_net_label(dealer_net),
        chip_concentration=concentration,
        chip_trend=trend,
        chip_description=description,
        margin_balance_change=margin_balance_change,
        short_balance_change=short_balance_change,
    )


def _prepare_institutional(df: pd.DataFrame) -> pd.DataFrame:
    required = {
        "date",
        "foreign_net",
        "trust_net",
        "dealer_net",
    }
    if not isinstance(df, pd.DataFrame) or df.empty or not required.issubset(df.columns):
        return pd.DataFrame(columns=sorted(required))

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date")
    for col in ("foreign_net", "trust_net", "dealer_net"):
        out[col] = pd.to_numeric(out[col], errors="coerce").fillna(0).astype("int64")
    return out.reset_index(drop=True)


def _prepare_margin(df: pd.DataFrame) -> pd.DataFrame:
    required = {"date", "margin_balance", "short_balance"}
    if not isinstance(df, pd.DataFrame) or df.empty or not required.issubset(df.columns):
        return pd.DataFrame(columns=sorted(required))

    out = df.copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce")
    out = out.dropna(subset=["date"]).sort_values("date")
    out["margin_balance"] = pd.to_numeric(out["margin_balance"], errors="coerce").fillna(0).astype("int64")
    out["short_balance"] = pd.to_numeric(out["short_balance"], errors="coerce").fillna(0).astype("int64")
    return out.reset_index(drop=True)


def _shares_to_lots(shares: float) -> int:
    return int(float(shares) / 1000.0)


def _format_net_label(net_lots: int) -> str:
    if net_lots > 0:
        return f"買超 {net_lots} 張"
    if net_lots < 0:
        return f"賣超 {abs(net_lots)} 張"
    return "持平 0 張"


def _sign_int(value: float) -> int:
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def _determine_concentration(signs: pd.Series) -> str:
    if signs.empty:
        return "穩定"
    if (signs > 0).all():
        return "集中"
    if (signs < 0).all():
        return "分散"
    return "穩定"
