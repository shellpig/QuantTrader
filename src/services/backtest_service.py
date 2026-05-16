"""Backtest service — non-UI orchestration layer (Phase 10-A).

All functions return plain Python objects / dataclasses.
No Streamlit calls are made here.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, Callable

import pandas as pd

from src.backtest.batch import StrategyRunSummary, run_strategy_batch
from src.backtest.cost import create_cost_calculator
from src.backtest.dca import DcaBacktestResult, run_dca_backtest
from src.backtest.engine_event import EventDrivenBacktester
from src.backtest.engine_vec import VectorizedBacktester
from src.backtest.metrics import BacktestResult
from src.backtest.sweep import MAX_COMBOS, SWEEP_PARAM_SPECS, generate_param_grid
from src.core.config import get_config
from src.core.exceptions import FetcherError
from src.core.market import get_market_spec, normalize_market, normalize_symbol
from src.core.strategy_config import get_strategy_presets
from src.data.cleaner import DataCleaner
from src.data.fetcher import FinMindFetcher, IDataFetcher, YFinanceFetcher
from src.data.maintenance import DataMaintenance
from src.data.storage import DuckDBMeta, ParquetStorage
from src.strategy.examples.bias import BiasStrategy
from src.strategy.examples.bollinger_band import BollingerBandStrategy
from src.strategy.examples.donchian_breakout import DonchianBreakoutStrategy
from src.strategy.examples.kd_cross import KDCrossStrategy
from src.strategy.examples.ma_cross import MACrossStrategy
from src.strategy.examples.macd_cross import MACDCrossStrategy
from src.strategy.examples.rsi import RSIStrategy

_VECTOR_ENGINE = "vectorized"
_EVENT_ENGINE = "event_driven"

_SUPPORTED_TYPES = {
    "moving_average_cross",
    "dollar_cost_averaging",
    "rsi",
    "kd_cross",
    "macd_cross",
    "bollinger_band",
    "bias",
    "donchian_breakout",
}

_SWEEP_PARAM_TYPES: dict[str, str] = {
    "short_window": "int",
    "long_window": "int",
    "period": "int",
    "oversold": "float",
    "overbought": "float",
    "k_period": "int",
    "d_period": "int",
    "smooth_k": "int",
    "fast": "int",
    "slow": "int",
    "signal": "int",
    "std_dev": "float",
    "ma_period": "int",
    "buy_bias": "float",
    "sell_bias": "float",
    "entry_period": "int",
    "exit_period": "int",
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class BacktestJobResult:
    """Wraps the raw BacktestResult / DcaBacktestResult with metadata."""

    symbol: str
    market: str
    strategy_type: str
    strategy_params: dict[str, Any]
    currency: str
    engine: str
    result: BacktestResult | None = None
    dca_result: DcaBacktestResult | None = None
    data: pd.DataFrame = field(default_factory=pd.DataFrame)
    dca_warning: str | None = None
    error: str | None = None


@dataclass
class BacktestServiceError:
    code: str     # e.g. "INVALID_SYMBOL", "NO_DATA", "INVALID_PARAMS"
    message: str


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_backtest_data(
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    *,
    market: str = "tw",
    require_adjusted: bool = True,
) -> pd.DataFrame | BacktestServiceError:
    """Load and auto-sync daily data for backtest.

    Returns a filtered DataFrame or a ``BacktestServiceError``.
    """
    normalized_market = normalize_market(market)
    timezone = get_market_spec(normalized_market).timezone
    storage = ParquetStorage()

    try:
        _sync_symbol_daily_data(symbol, storage, market=normalized_market)
    except FetcherError as exc:
        return BacktestServiceError(code="FETCH_FAILED", message=str(exc))
    except Exception as exc:  # noqa: BLE001
        return BacktestServiceError(code="FETCH_FAILED", message=str(exc))

    df = storage.load_adjusted(symbol, market=normalized_market)
    if df.empty and require_adjusted:
        return BacktestServiceError(
            code="NO_ADJUSTED_DATA",
            message=(
                f"{symbol} adjusted data is missing. "
                "Please run rebuild before backtest."
            ),
        )
    if df.empty:
        df = storage.load_daily(symbol, market=normalized_market)
    if df.empty:
        return BacktestServiceError(code="NO_DATA", message=f"{symbol} 無可用日線資料。")

    data = df.copy()
    data["date"] = pd.to_datetime(data["date"], errors="coerce")
    data = data.dropna(subset=["date"]).copy()
    if data["date"].dt.tz is None:
        data["date"] = data["date"].dt.tz_localize(timezone)
    else:
        data["date"] = data["date"].dt.tz_convert(timezone)

    for col in ("open", "high", "low", "close"):
        data[col] = pd.to_numeric(data[col], errors="coerce")
    data = data.dropna(subset=["open", "high", "low", "close"])
    data = data[(data["date"] >= start_ts) & (data["date"] < end_exclusive)].copy()
    return data.sort_values("date").reset_index(drop=True)


def build_strategy(
    strategy_type: str,
    params: dict[str, Any],
) -> object | BacktestServiceError:
    """Instantiate a strategy from type + params dict.

    Returns the strategy object or a ``BacktestServiceError``.
    """
    try:
        if strategy_type == "moving_average_cross":
            ma_short = int(params.get("short_window", 20))
            ma_long = int(params.get("long_window", 60))
            if ma_short >= ma_long:
                return BacktestServiceError(
                    code="INVALID_PARAMS",
                    message="short_window 必須小於 long_window。",
                )
            return MACrossStrategy(ma_short=ma_short, ma_long=ma_long)

        if strategy_type == "rsi":
            return RSIStrategy(
                period=int(params.get("period", 14)),
                oversold=float(params.get("oversold", 30)),
                overbought=float(params.get("overbought", 70)),
            )

        if strategy_type == "kd_cross":
            return KDCrossStrategy(
                k_period=int(params.get("k_period", 9)),
                d_period=int(params.get("d_period", 3)),
                smooth_k=int(params.get("smooth_k", 3)),
            )

        if strategy_type == "macd_cross":
            return MACDCrossStrategy(
                fast=int(params.get("fast", 12)),
                slow=int(params.get("slow", 26)),
                signal=int(params.get("signal", 9)),
            )

        if strategy_type == "bollinger_band":
            return BollingerBandStrategy(
                period=int(params.get("period", 20)),
                std_dev=float(params.get("std_dev", 2.0)),
            )

        if strategy_type == "bias":
            return BiasStrategy(
                ma_period=int(params.get("ma_period", 20)),
                buy_bias=float(params.get("buy_bias", -10.0)),
                sell_bias=float(params.get("sell_bias", 10.0)),
            )

        if strategy_type == "donchian_breakout":
            return DonchianBreakoutStrategy(
                entry_period=int(params.get("entry_period", 20)),
                exit_period=int(params.get("exit_period", 10)),
            )

        return BacktestServiceError(
            code="UNSUPPORTED_STRATEGY",
            message=f"目前不支援策略類型：{strategy_type}",
        )

    except (ValueError, TypeError) as exc:
        return BacktestServiceError(code="INVALID_PARAMS", message=str(exc))


def run_backtest_job(
    *,
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    strategy_preset: dict[str, Any],
    engine: str = _VECTOR_ENGINE,
    market: str = "tw",
    initial_capital: float = 1_000_000,
) -> BacktestJobResult | BacktestServiceError:
    """Run a single backtest and return a ``BacktestJobResult``.

    Handles data loading, strategy instantiation, and engine dispatch.
    Returns ``BacktestServiceError`` on validation failures before execution.
    Execution errors are captured in ``BacktestJobResult.error``.
    """
    normalized_market = normalize_market(market)
    market_spec = get_market_spec(normalized_market)
    strategy_type = str(strategy_preset.get("type", "")).strip().lower()
    strategy_params: dict[str, Any] = (
        strategy_preset.get("params", {})
        if isinstance(strategy_preset.get("params"), dict)
        else {}
    )

    # ── load data ─────────────────────────────────────────────────────────
    data = load_backtest_data(
        symbol,
        start_ts,
        end_exclusive,
        market=normalized_market,
        require_adjusted=(strategy_type != "dollar_cost_averaging"),
    )
    if isinstance(data, BacktestServiceError):
        return data

    # ── DCA special path ─────────────────────────────────────────────────
    if strategy_type == "dollar_cost_averaging":
        dca_warning: str | None = None
        if normalized_market == "us":
            dca_warning = (
                "US-1 DCA 最小買入單位為 1 整股，不支援碎股。"
                "若每月投入金額低於股價，該期可能不會買進。"
            )
        try:
            dca_result = run_dca_backtest(
                data=data,
                symbol=symbol,
                start_ts=start_ts,
                end_exclusive=end_exclusive,
                params=strategy_params,
                cost_calculator=create_cost_calculator(market=normalized_market),
                market=normalized_market,
            )
        except Exception as exc:  # noqa: BLE001
            return BacktestJobResult(
                symbol=symbol,
                market=normalized_market,
                strategy_type=strategy_type,
                strategy_params=strategy_params,
                currency=market_spec.currency,
                engine="dca",
                data=data,
                error=str(exc),
            )
        return BacktestJobResult(
            symbol=symbol,
            market=normalized_market,
            strategy_type=strategy_type,
            strategy_params=strategy_params,
            currency=market_spec.currency,
            engine="dca",
            dca_result=dca_result,
            data=data,
            dca_warning=dca_warning,
        )

    # ── standard strategy path ────────────────────────────────────────────
    if data.empty:
        return BacktestServiceError(code="NO_DATA", message="資料區間內沒有可用日線資料。")

    strategy_obj = build_strategy(strategy_type, strategy_params)
    if isinstance(strategy_obj, BacktestServiceError):
        return strategy_obj

    cost_calculator = create_cost_calculator(market=normalized_market)
    engine_obj = (
        VectorizedBacktester(initial_capital=initial_capital, cost_calculator=cost_calculator)
        if engine == _VECTOR_ENGINE
        else EventDrivenBacktester(initial_capital=initial_capital, cost_calculator=cost_calculator)
    )
    try:
        result = engine_obj.run(strategy=strategy_obj, data=data)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        return BacktestJobResult(
            symbol=symbol,
            market=normalized_market,
            strategy_type=strategy_type,
            strategy_params=strategy_params,
            currency=market_spec.currency,
            engine=engine,
            data=data,
            error=str(exc),
        )

    return BacktestJobResult(
        symbol=symbol,
        market=normalized_market,
        strategy_type=strategy_type,
        strategy_params=strategy_params,
        currency=market_spec.currency,
        engine=engine,
        result=result,
        data=data,
    )


def list_strategy_presets() -> list[dict[str, Any]]:
    """Return current strategy presets from config."""
    return get_strategy_presets(get_config())


def run_batch_backtest_job(
    *,
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    presets: list[dict[str, Any]],
    market: str = "tw",
    initial_capital: float = 1_000_000,
) -> dict[str, Any] | BacktestServiceError:
    """Run batch strategy comparison and return JSON-safe payload.

    Notes:
    - price_data is returned once at the top-level.
    - each summary may carry a `detail` payload for row expansion.
    """
    normalized_market = normalize_market(market)
    market_spec = get_market_spec(normalized_market)

    data = load_backtest_data(
        symbol,
        start_ts,
        end_exclusive,
        market=normalized_market,
        require_adjusted=True,
    )
    if isinstance(data, BacktestServiceError):
        return data

    batch_result = run_strategy_batch(
        data=data,
        symbol=symbol,
        start_date=str(start_ts.date()),
        end_date=str((end_exclusive - pd.Timedelta(days=1)).date()),
        presets=presets,
        initial_capital=initial_capital,
        cost_calculator=create_cost_calculator(market=normalized_market),
    )

    summaries: list[dict[str, Any]] = []
    for idx, (preset, summary) in enumerate(zip(presets, batch_result.summaries, strict=False)):
        summaries.append(
            _serialize_batch_summary(
                preset_index=idx,
                preset=preset,
                summary=summary,
                symbol=symbol,
                market=normalized_market,
                currency=market_spec.currency,
            )
        )

    return {
        "symbol": symbol,
        "market": normalized_market,
        "currency": market_spec.currency,
        "engine": "vectorized",
        "start_date": str(start_ts.date()),
        "end_date": str((end_exclusive - pd.Timedelta(days=1)).date()),
        "price_data": _serialize_price_data(data),
        "summaries": summaries,
    }


def build_batch_csv_blob(batch_payload: dict[str, Any]) -> io.StringIO:
    """Build in-memory CSV blob for backtest_batch result."""
    summaries = batch_payload.get("summaries", [])
    rows: list[dict[str, Any]] = []

    for s in summaries:
        total_return = s.get("total_return")
        annual_return = s.get("annual_return")
        max_drawdown = s.get("max_drawdown")
        sharpe_ratio = s.get("sharpe_ratio")
        win_rate = s.get("win_rate")
        profit_factor = s.get("profit_factor")
        total_trades = s.get("total_trades")

        rows.append({
            "策略名稱": s.get("preset_name", ""),
            "策略類型": s.get("strategy_type", ""),
            "總報酬": _fmt_pct(total_return),
            "年化報酬": _fmt_pct(annual_return),
            "最大回撤": _fmt_pct(max_drawdown),
            "Sharpe": _fmt_num(sharpe_ratio, 2),
            "勝率": _fmt_pct(win_rate),
            "Profit Factor": _fmt_profit_factor(profit_factor),
            "交易次數": int(total_trades or 0),
            "錯誤": s.get("error") or "",
        })

    buffer = io.StringIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer


def run_sweep_job(
    *,
    symbol: str,
    start_ts: pd.Timestamp,
    end_exclusive: pd.Timestamp,
    strategy_type: str,
    param_candidates: dict[str, list[Any]],
    market: str = "tw",
    initial_capital: float = 1_000_000,
    on_progress: Callable[[int, int, dict[str, Any]], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, Any] | BacktestServiceError:
    """Run parameter sweep and return JSON-safe payload for 10-E-3."""
    normalized_market = normalize_market(market)
    market_spec = get_market_spec(normalized_market)
    validated = validate_sweep_request(
        strategy_type=strategy_type,
        param_candidates=param_candidates,
    )
    if isinstance(validated, BacktestServiceError):
        return validated

    strategy_type = validated["strategy_type"]
    normalized_candidates = validated["param_candidates"]
    total_combos = validated["total_combos"]
    valid_list = validated["valid_params_list"]
    valid_combos = validated["valid_combos"]

    data = load_backtest_data(
        symbol,
        start_ts,
        end_exclusive,
        market=normalized_market,
        require_adjusted=True,
    )
    if isinstance(data, BacktestServiceError):
        return data

    calculator = create_cost_calculator(market=normalized_market)
    results: list[dict[str, Any]] = []

    for idx, params in enumerate(valid_list, start=1):
        if should_cancel is not None and should_cancel():
            break

        if _should_emit_sweep_progress(idx, valid_combos):
            on_progress and on_progress(idx, valid_combos, params)

        strategy_obj = build_strategy(strategy_type, params)
        if isinstance(strategy_obj, BacktestServiceError):
            results.append({
                "params": params,
                "total_return": None,
                "annual_return": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
                "win_rate": None,
                "profit_factor": None,
                "total_trades": 0,
                "error": strategy_obj.message,
                "sample_warning": False,
            })
            continue

        engine = VectorizedBacktester(
            initial_capital=initial_capital,
            cost_calculator=calculator,
        )
        try:
            bt = engine.run(strategy=strategy_obj, data=data)  # type: ignore[arg-type]
            results.append({
                "params": params,
                "total_return": round(float(bt.total_return), 6),
                "annual_return": round(float(bt.annual_return), 6),
                "max_drawdown": round(float(bt.max_drawdown), 6),
                "sharpe_ratio": round(float(bt.sharpe_ratio), 4),
                "win_rate": round(float(bt.win_rate), 4),
                "profit_factor": round(float(bt.profit_factor), 4),
                "total_trades": int(bt.total_trades),
                "error": None,
                "sample_warning": int(bt.total_trades) < 3,
            })
        except Exception as exc:  # noqa: BLE001
            results.append({
                "params": params,
                "total_return": None,
                "annual_return": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
                "win_rate": None,
                "profit_factor": None,
                "total_trades": 0,
                "error": str(exc),
                "sample_warning": False,
            })

    return {
        "symbol": symbol,
        "market": normalized_market,
        "currency": market_spec.currency,
        "strategy_type": strategy_type,
        "start_date": str(start_ts.date()),
        "end_date": str((end_exclusive - pd.Timedelta(days=1)).date()),
        "total_combos": int(total_combos),
        "valid_combos": int(valid_combos),
        "max_combos_limit": int(MAX_COMBOS),
        "results": results,
    }


def validate_sweep_request(
    *,
    strategy_type: str,
    param_candidates: dict[str, list[Any]],
) -> dict[str, Any] | BacktestServiceError:
    """Validate and normalize sweep request before creating/running jobs."""
    normalized_type = str(strategy_type).strip().lower()
    if normalized_type not in SWEEP_PARAM_SPECS:
        return BacktestServiceError(
            code="UNSUPPORTED_STRATEGY",
            message=f"不支援參數掃描的策略類型：{strategy_type}",
        )

    normalized_candidates = _normalize_sweep_candidates(normalized_type, param_candidates)
    if isinstance(normalized_candidates, BacktestServiceError):
        return normalized_candidates

    total_combos, valid_list = generate_param_grid(normalized_type, normalized_candidates)
    valid_combos = len(valid_list)
    if valid_combos > MAX_COMBOS:
        return BacktestServiceError(
            code="OVER_MAX_COMBOS",
            message=f"合法組合數 {valid_combos} 超過上限 {MAX_COMBOS}，請縮小參數範圍。",
        )

    return {
        "strategy_type": normalized_type,
        "param_candidates": normalized_candidates,
        "total_combos": int(total_combos),
        "valid_combos": int(valid_combos),
        "valid_params_list": valid_list,
    }


def build_sweep_csv_blob(sweep_payload: dict[str, Any]) -> io.StringIO:
    """Build in-memory CSV blob for backtest_sweep result."""
    rows: list[dict[str, Any]] = []
    for item in sweep_payload.get("results", []):
        params = item.get("params", {})
        row = {
            **(params if isinstance(params, dict) else {}),
            "總報酬": _fmt_pct(item.get("total_return")) if item.get("error") is None else "—",
            "年化報酬": _fmt_pct(item.get("annual_return")) if item.get("error") is None else "—",
            "最大回撤": _fmt_pct(item.get("max_drawdown")) if item.get("error") is None else "—",
            "Sharpe": _fmt_num(item.get("sharpe_ratio"), 2) if item.get("error") is None else "—",
            "勝率": _fmt_pct(item.get("win_rate")) if item.get("error") is None else "—",
            "Profit Factor": _fmt_profit_factor(item.get("profit_factor")) if item.get("error") is None else "—",
            "交易次數": int(item.get("total_trades", 0)) if item.get("error") is None else "—",
            "sample_warning": bool(item.get("sample_warning", False)),
            "錯誤": item.get("error") or "",
        }
        rows.append(row)

    buffer = io.StringIO()
    pd.DataFrame(rows).to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _sync_symbol_daily_data(
    symbol: str,
    storage: ParquetStorage,
    market: str = "tw",
) -> None:
    normalized_market = normalize_market(market)
    fetchers = _build_fetchers_from_config(market=normalized_market)
    if not fetchers:
        raise FetcherError(f"{symbol} 自動更新日線資料失敗：No available data source. Details: n/a")

    errors: list[str] = []
    for source, fetcher in fetchers:
        meta = DuckDBMeta()
        try:
            maintenance = DataMaintenance(
                fetcher=fetcher,
                storage=storage,
                meta=meta,
                cleaner=DataCleaner(),
            )
            maintenance.update_daily(symbol, market=normalized_market)
            return
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{source}: {exc}")
        finally:
            meta.close()

    raise FetcherError(f"{symbol} 自動更新日線資料失敗：{' | '.join(errors)}")


def serialize_backtest_result(job_result: "BacktestJobResult") -> dict[str, Any]:
    """Convert BacktestJobResult → JSON-safe dict matching the 10-E-1 result schema."""
    market = job_result.market
    currency = job_result.currency
    strategy_type = job_result.strategy_type

    price_data = _serialize_price_data(job_result.data)

    # ── DCA branch ────────────────────────────────────────────────────────
    if job_result.dca_result is not None:
        dca = job_result.dca_result
        equity_curve = _dca_equity_curve(dca.transactions, job_result.data)
        return {
            "symbol": job_result.symbol,
            "market": market,
            "currency": currency,
            "engine": job_result.engine,
            "strategy_type": strategy_type,
            "strategy_params": job_result.strategy_params,
            "metrics": {
                "total_trades": None,
                "total_return": round(float(dca.total_return_rate), 6),
                "annual_return": None,
                "max_drawdown": None,
                "max_drawdown_start": None,
                "max_drawdown_end": None,
                "sharpe_ratio": None,
                "win_rate": None,
                "profit_factor": None,
            },
            "equity_curve": equity_curve,
            "trades": [],
            "signals": [],
            "price_data": price_data,
            "dca_warning": job_result.dca_warning,
        }

    # ── error branch (execution failed) ──────────────────────────────────
    if job_result.result is None:
        return {
            "symbol": job_result.symbol,
            "market": market,
            "currency": currency,
            "engine": job_result.engine,
            "strategy_type": strategy_type,
            "strategy_params": job_result.strategy_params,
            "metrics": None,
            "equity_curve": [],
            "trades": [],
            "signals": [],
            "price_data": price_data,
            "dca_warning": None,
            "error": job_result.error,
        }

    # ── standard backtest branch ──────────────────────────────────────────
    r = job_result.result
    equity_curve = _serialize_equity_curve(r.equity_curve)
    trades = _serialize_trades(r.trades)
    signals = _signals_from_trades(r.trades)

    return {
        "symbol": job_result.symbol,
        "market": market,
        "currency": currency,
        "engine": job_result.engine,
        "strategy_type": strategy_type,
        "strategy_params": job_result.strategy_params,
        "metrics": {
            "total_trades": int(r.total_trades),
            "total_return": round(float(r.total_return), 6),
            "annual_return": round(float(r.annual_return), 6),
            "max_drawdown": round(float(r.max_drawdown), 6),
            "max_drawdown_start": str(r.max_drawdown_start) if r.max_drawdown_start else None,
            "max_drawdown_end": str(r.max_drawdown_end) if r.max_drawdown_end else None,
            "sharpe_ratio": round(float(r.sharpe_ratio), 4),
            "win_rate": round(float(r.win_rate), 4),
            "profit_factor": round(float(r.profit_factor), 4),
        },
        "equity_curve": equity_curve,
        "trades": trades,
        "signals": signals,
        "price_data": price_data,
        "dca_warning": None,
    }


def _serialize_price_data(data: pd.DataFrame) -> list[dict[str, Any]]:
    if data is None or data.empty:
        return []
    rows = []
    for _, row in data.iterrows():
        date_val = row.get("date") or row.name
        try:
            date_str = str(pd.Timestamp(date_val).date())
        except Exception:  # noqa: BLE001
            date_str = str(date_val)[:10]
        rows.append({
            "date": date_str,
            "open": float(row.get("open", 0) or 0),
            "high": float(row.get("high", 0) or 0),
            "low": float(row.get("low", 0) or 0),
            "close": float(row.get("close", 0) or 0),
            "volume": int(float(row.get("volume", 0) or 0)),
        })
    return rows


def _serialize_equity_curve(equity_series: pd.Series) -> list[dict[str, Any]]:
    if equity_series is None or equity_series.empty:
        return []
    rows = []
    for dt, val in equity_series.items():
        try:
            date_str = str(pd.Timestamp(dt).date())
        except Exception:  # noqa: BLE001
            date_str = str(dt)[:10]
        rows.append({"date": date_str, "value": round(float(val), 2)})
    return rows


def _serialize_trades(trades_df: pd.DataFrame) -> list[dict[str, Any]]:
    if trades_df is None or trades_df.empty:
        return []
    rows = []
    for _, row in trades_df.iterrows():
        entry_price = float(row.get("entry_price", 0) or 0)
        shares = int(float(row.get("quantity", 0) or 0))
        pnl = float(row.get("pnl", 0) or 0)
        cost_basis = entry_price * shares
        return_pct = round(pnl / cost_basis, 6) if cost_basis != 0 else 0.0
        try:
            entry_date = str(pd.Timestamp(row["entry_date"]).date())
        except Exception:  # noqa: BLE001
            entry_date = str(row.get("entry_date", ""))[:10]
        try:
            exit_date = str(pd.Timestamp(row["exit_date"]).date())
        except Exception:  # noqa: BLE001
            exit_date = str(row.get("exit_date", ""))[:10]
        rows.append({
            "entry_date": entry_date,
            "exit_date": exit_date,
            "side": str(row.get("side", "long")).lower(),
            "entry_price": entry_price,
            "exit_price": float(row.get("exit_price", 0) or 0),
            "shares": shares,
            "pnl": round(pnl, 2),
            "return_pct": return_pct,
        })
    return rows


def _signals_from_trades(trades_df: pd.DataFrame) -> list[dict[str, Any]]:
    if trades_df is None or trades_df.empty:
        return []
    signals = []
    for _, row in trades_df.iterrows():
        try:
            entry_date = str(pd.Timestamp(row["entry_date"]).date())
        except Exception:  # noqa: BLE001
            entry_date = str(row.get("entry_date", ""))[:10]
        try:
            exit_date = str(pd.Timestamp(row["exit_date"]).date())
        except Exception:  # noqa: BLE001
            exit_date = str(row.get("exit_date", ""))[:10]
        signals.append({"date": entry_date, "side": "buy", "price": float(row.get("entry_price", 0) or 0)})
        signals.append({"date": exit_date, "side": "sell", "price": float(row.get("exit_price", 0) or 0)})
    return signals


def _serialize_batch_summary(
    *,
    preset_index: int,
    preset: dict[str, Any],
    summary: StrategyRunSummary,
    symbol: str,
    market: str,
    currency: str,
) -> dict[str, Any]:
    strategy_params = preset.get("params", {}) if isinstance(preset.get("params"), dict) else {}
    detail: dict[str, Any] | None = None

    if summary.result is not None and summary.error is None:
        detail_payload = serialize_backtest_result(
            BacktestJobResult(
                symbol=symbol,
                market=market,
                strategy_type=summary.strategy_type,
                strategy_params=strategy_params,
                currency=currency,
                engine="vectorized",
                result=summary.result,
                data=pd.DataFrame(),
            )
        )
        detail_payload.pop("price_data", None)
        detail = detail_payload

    return {
        "preset_index": preset_index,
        "preset_name": summary.preset_name,
        "strategy_type": summary.strategy_type,
        "strategy_params": strategy_params,
        "total_return": round(float(summary.total_return), 6) if summary.error is None else None,
        "annual_return": round(float(summary.annual_return), 6) if summary.error is None else None,
        "max_drawdown": round(float(summary.max_drawdown), 6) if summary.error is None else None,
        "sharpe_ratio": round(float(summary.sharpe_ratio), 4) if summary.error is None else None,
        "win_rate": round(float(summary.win_rate), 4) if summary.error is None else None,
        "profit_factor": round(float(summary.profit_factor), 4) if summary.error is None else None,
        "total_trades": int(summary.total_trades),
        "error": summary.error,
        "detail": detail,
    }


def _dca_equity_curve(transactions: pd.DataFrame, price_data: pd.DataFrame) -> list[dict[str, Any]]:
    """Derive daily equity curve from DCA transactions + price data."""
    if price_data is None or price_data.empty:
        return []
    if transactions is None or transactions.empty:
        return []

    price = price_data.copy()
    price["_date_key"] = pd.to_datetime(price["date"]).dt.tz_localize(None).dt.normalize()

    tx = transactions.copy()
    tx["_date_key"] = pd.to_datetime(tx["date"]).dt.tz_localize(None).dt.normalize()
    tx_sorted = tx.dropna(subset=["_date_key"]).sort_values("_date_key")
    tx_rows = tx_sorted.to_dict("records")

    tx_idx = 0
    cum_shares = 0
    cash = 0.0
    result = []

    for _, row in price.iterrows():
        day = row["_date_key"]
        while tx_idx < len(tx_rows):
            tx_day = pd.Timestamp(tx_rows[tx_idx]["_date_key"])
            if tx_day <= day:
                cum_shares = int(tx_rows[tx_idx].get("cumulative_shares", cum_shares))
                cash = float(tx_rows[tx_idx].get("cash_balance", cash))
                tx_idx += 1
            else:
                break
        close = float(row.get("close", 0) or 0)
        value = round(cum_shares * close + cash, 2)
        result.append({"date": str(day.date()), "value": value})

    return result


def _fmt_pct(value: Any) -> str:
    if value is None:
        return ""
    return f"{float(value) * 100:.2f}%"


def _fmt_num(value: Any, digits: int) -> str:
    if value is None:
        return ""
    return f"{float(value):.{digits}f}"


def _fmt_profit_factor(value: Any) -> str:
    if value is None:
        return ""
    pf = float(value)
    if pf >= 999.0:
        return "N/A"
    return f"{pf:.2f}"


def _should_emit_sweep_progress(current: int, total: int) -> bool:
    if total <= 0:
        return False
    if total > 50:
        return (current % 5 == 0) or (current == total)
    return True


def _normalize_sweep_candidates(
    strategy_type: str,
    param_candidates: dict[str, list[Any]],
) -> dict[str, list[Any]] | BacktestServiceError:
    expected_keys = SWEEP_PARAM_SPECS.get(strategy_type)
    if expected_keys is None:
        return BacktestServiceError(
            code="UNSUPPORTED_STRATEGY",
            message=f"不支援參數掃描的策略類型：{strategy_type}",
        )

    provided_keys = set(param_candidates.keys())
    if provided_keys != set(expected_keys):
        return BacktestServiceError(
            code="INVALID_PARAMS",
            message=f"param_candidates 必須包含：{', '.join(expected_keys)}",
        )

    normalized: dict[str, list[Any]] = {}
    for key in expected_keys:
        raw_values = param_candidates.get(key)
        if not isinstance(raw_values, list) or len(raw_values) == 0:
            return BacktestServiceError(
                code="INVALID_PARAMS",
                message=f"參數 {key} 需為非空 list",
            )

        values: list[Any] = []
        for raw in raw_values:
            try:
                as_num = float(raw)
            except (TypeError, ValueError):
                return BacktestServiceError(
                    code="INVALID_PARAMS",
                    message=f"參數 {key} 含非數值項目：{raw}",
                )

            expected_type = _SWEEP_PARAM_TYPES.get(key, "float")
            if expected_type == "int":
                if not as_num.is_integer():
                    return BacktestServiceError(
                        code="INVALID_PARAMS",
                        message=f"參數 {key} 必須是整數：{raw}",
                    )
                values.append(int(as_num))
            else:
                values.append(float(as_num))
        normalized[key] = values
    return normalized


def _build_fetchers_from_config(market: str = "tw") -> list[tuple[str, IDataFetcher]]:
    normalized_market = normalize_market(market)
    cfg = get_config()
    data_section = cfg.get("data", {}) if isinstance(cfg, dict) else {}
    primary = str(data_section.get("primary_source", "finmind")).strip().lower()
    fallback = str(data_section.get("fallback_source", "yfinance")).strip().lower()
    order = [primary, fallback]

    fetchers: list[tuple[str, IDataFetcher]] = []
    for source in order:
        if source in {name for name, _ in fetchers}:
            continue
        try:
            if source == "finmind" and normalized_market == "tw":
                fetchers.append((source, FinMindFetcher()))
            elif source == "yfinance":
                fetchers.append((source, YFinanceFetcher(market=normalized_market)))
        except Exception:  # noqa: BLE001
            continue
    return fetchers
