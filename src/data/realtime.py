"""Realtime quote fetcher for Phase 8-D."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import time
from typing import Any
import warnings
from zoneinfo import ZoneInfo

import requests

from src.core.constants import TAIPEI_TZ
from src.core.config import get_config
from src.core.exceptions import FetcherError


@dataclass
class RealtimeQuote:
    symbol: str
    name: str
    price: float
    change: float
    change_pct: float
    open: float
    high: float
    low: float
    yesterday_close: float
    volume: int
    timestamp: str
    trade_date: str | None = None
    best_bid: list[float] = field(default_factory=list)
    best_ask: list[float] = field(default_factory=list)
    best_bid_vol: list[int] = field(default_factory=list)
    best_ask_vol: list[int] = field(default_factory=list)
    is_market_open: bool = True
    is_estimated_price: bool = False
    price_label: str = "成交價"
    estimated_price: float | None = None


@dataclass
class BidAskStructure:
    total_bid_vol: int
    total_ask_vol: int
    bid_ratio: float
    ask_ratio: float
    label: str


class RealtimeFetcher:
    """Realtime quote fetcher with TWSE routing and cache."""

    BASE_URL = "https://mis.twse.com.tw/stock/api/getStockInfo.jsp"
    FINMIND_URL = "https://api.finmindtrade.com/api/v4/data"

    def __init__(
        self,
        cache_ttl: int = 10,
        request_timeout: int = 5,
        *,
        session: requests.Session | None = None,
        clock: Any | None = None,
    ):
        self._market_map: dict[str, str] = {}
        self._cache: dict[str, tuple[float, RealtimeQuote]] = {}
        self._cache_ttl = max(0, int(cache_ttl))
        self._request_timeout = max(1, int(request_timeout))
        self._session = session or requests.Session()
        self._clock = clock or time.time

    @classmethod
    def from_config(cls) -> RealtimeFetcher:
        cfg = get_config()
        rt = cfg.get("realtime", {}) if isinstance(cfg, dict) else {}
        if not isinstance(rt, dict):
            rt = {}
        return cls(
            cache_ttl=int(rt.get("cache_ttl", 10)),
            request_timeout=int(rt.get("request_timeout", 5)),
        )

    def fetch_quote(self, symbol: str) -> RealtimeQuote:
        symbol = str(symbol).strip()
        if not symbol:
            raise FetcherError("symbol is required for realtime quote fetch.")

        now = float(self._clock())
        cached = self._cache.get(symbol)
        if cached is not None:
            cached_ts, cached_quote = cached
            if now - cached_ts <= self._cache_ttl:
                return cached_quote

        quote = self._fetch_quote_from_api(symbol)
        self._cache[symbol] = (now, quote)
        return quote

    def fetch_bid_ask_structure(self, quote: RealtimeQuote) -> BidAskStructure:
        if quote.best_bid_vol and quote.best_ask_vol:
            total_bid = int(sum(quote.best_bid_vol))
            total_ask = int(sum(quote.best_ask_vol))
            denom = total_bid + total_ask
            if denom > 0:
                bid_ratio = total_bid / denom
                ask_ratio = total_ask / denom
            else:
                bid_ratio = ask_ratio = 0.5
        else:
            total_bid = 0
            total_ask = 0
            spread = float(quote.high - quote.low)
            if spread > 0:
                momentum = (float(quote.price) - float(quote.open)) / spread
                bid_ratio = min(max(0.5 + momentum * 0.5, 0.0), 1.0)
                ask_ratio = 1.0 - bid_ratio
            else:
                bid_ratio = ask_ratio = 0.5

        if bid_ratio > 0.55:
            label = "買盤較積極"
        elif ask_ratio > 0.55:
            label = "賣壓較重"
        else:
            label = "多空均衡"

        return BidAskStructure(
            total_bid_vol=total_bid,
            total_ask_vol=total_ask,
            bid_ratio=round(float(bid_ratio), 4),
            ask_ratio=round(float(ask_ratio), 4),
            label=label,
        )

    def load_market_map(self) -> None:
        cfg = get_config()
        token = ""
        if isinstance(cfg, dict):
            secrets = cfg.get("secrets", {})
            if isinstance(secrets, dict):
                token = str(secrets.get("finmind_token", "")).strip()

        headers = {"Authorization": f"Bearer {token}"} if token else {}
        params = {"dataset": "TaiwanStockInfo"}
        try:
            resp = self._session.get(
                self.FINMIND_URL,
                params=params,
                headers=headers,
                timeout=self._request_timeout,
            )
            resp.raise_for_status()
            payload = resp.json()
            data = payload.get("data", []) if isinstance(payload, dict) else []
            mapping: dict[str, str] = {}
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    symbol = str(item.get("stock_id", "")).strip()
                    market_type = str(item.get("type", "")).strip().lower()
                    if not symbol:
                        continue
                    if market_type == "twse":
                        mapping[symbol] = "tse"
                    elif market_type == "tpex":
                        mapping[symbol] = "otc"
            self._market_map = mapping
        except Exception:  # noqa: BLE001
            self._market_map = {}

    def _fetch_quote_from_api(self, symbol: str) -> RealtimeQuote:
        payload = self._request_quote_payload(symbol)
        return self._parse_twse_response(payload)

    def _build_ex_ch(self, symbol: str) -> str:
        if not self._market_map:
            self.load_market_map()
        market = self._market_map.get(symbol, "tse")
        prefix = "otc" if market == "otc" else "tse"
        return f"{prefix}_{symbol}.tw"

    def _request_quote_payload(self, symbol: str) -> dict[str, Any]:
        ex_ch = self._build_ex_ch(symbol)
        params = {
            "ex_ch": ex_ch,
            "json": "1",
            "delay": "0",
            "_": str(int(self._clock() * 1000)),
        }
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                response = self._session.get(
                    self.BASE_URL,
                    params=params,
                    timeout=self._request_timeout,
                    verify=False,
                )
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise FetcherError("Unexpected TWSE payload structure.")
            return payload
        except requests.RequestException as exc:
            raise FetcherError(f"TWSE realtime request failed for {symbol}.") from exc
        except ValueError as exc:
            raise FetcherError(f"TWSE realtime response decode failed for {symbol}.") from exc

    def _parse_twse_response(self, data: dict[str, Any]) -> RealtimeQuote:
        msg_array = data.get("msgArray", [])
        if not isinstance(msg_array, list) or not msg_array:
            raise FetcherError("TWSE realtime response has no quote data.")

        row = msg_array[0]
        if not isinstance(row, dict):
            raise FetcherError("TWSE realtime response row is invalid.")

        symbol = str(row.get("c", "")).strip()
        name = str(row.get("n", "")).strip()
        timestamp = str(row.get("t", "")).strip()
        trade_date = self._parse_trade_date(row.get("d") or row.get("^"))
        now = datetime.fromtimestamp(float(self._clock()), ZoneInfo(TAIPEI_TZ))
        is_market_open = self._is_market_open(timestamp, now=now)

        best_bid = self._parse_float_levels(row.get("b", ""))
        best_ask = self._parse_float_levels(row.get("a", ""))
        best_bid_vol = self._parse_int_levels(row.get("g", ""))
        best_ask_vol = self._parse_int_levels(row.get("f", ""))

        yesterday_close = self._safe_float(row.get("y"), default=0.0)
        raw_price = self._safe_float(row.get("z"), default=None)
        is_estimated_price = False
        price_label = "成交價"
        estimated_price: float | None = None
        if raw_price is not None:
            price = raw_price
        elif is_market_open:
            estimated_price = self._estimate_quote_price(best_bid, best_ask)
            # Keep `price` as a confirmed value only; midpoint estimate is stored separately.
            price = yesterday_close
            is_estimated_price = estimated_price is not None
            price_label = "昨收價(無成交)"
        else:
            price = yesterday_close
            is_estimated_price = True
            price_label = "昨收價(無成交)"
        open_price = self._safe_float(row.get("o"), default=price)
        high = self._safe_float(row.get("h"), default=price)
        low = self._safe_float(row.get("l"), default=price)
        volume = self._safe_int(row.get("v"), default=0)

        change = float(price - yesterday_close)
        change_pct = float((change / yesterday_close * 100.0) if yesterday_close else 0.0)

        return RealtimeQuote(
            symbol=symbol,
            name=name,
            price=float(price),
            change=change,
            change_pct=change_pct,
            open=float(open_price),
            high=float(high),
            low=float(low),
            yesterday_close=float(yesterday_close),
            volume=int(volume),
            timestamp=timestamp,
            trade_date=trade_date,
            best_bid=best_bid,
            best_ask=best_ask,
            best_bid_vol=best_bid_vol,
            best_ask_vol=best_ask_vol,
            is_market_open=is_market_open,
            is_estimated_price=is_estimated_price,
            price_label=price_label,
            estimated_price=estimated_price,
        )

    @staticmethod
    def _estimate_quote_price(best_bid: list[float], best_ask: list[float]) -> float | None:
        bid1 = best_bid[0] if best_bid else None
        ask1 = best_ask[0] if best_ask else None
        if bid1 is not None and ask1 is not None:
            return float((bid1 + ask1) / 2.0)
        if bid1 is not None:
            return float(bid1)
        if ask1 is not None:
            return float(ask1)
        return None

    @staticmethod
    def _parse_trade_date(value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text or text in {"-", "--"}:
            return None
        try:
            parsed = datetime.strptime(text, "%Y%m%d")
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d")

    @staticmethod
    def _safe_float(value: Any, *, default: float | None) -> float | None:
        if value is None:
            return default
        text = str(value).strip()
        if text in {"", "-", "--", "None", "nan"}:
            return default
        try:
            return float(text)
        except ValueError:
            return default

    @staticmethod
    def _safe_int(value: Any, *, default: int) -> int:
        if value is None:
            return default
        text = str(value).strip()
        if text in {"", "-", "--", "None", "nan"}:
            return default
        try:
            return int(float(text))
        except ValueError:
            return default

    @staticmethod
    def _parse_float_levels(raw: Any) -> list[float]:
        if raw is None:
            return []
        parts = [p.strip() for p in str(raw).split("_")]
        out: list[float] = []
        for p in parts:
            if not p or p in {"-", "--"}:
                continue
            try:
                out.append(float(p))
            except ValueError:
                continue
        return out

    @staticmethod
    def _parse_int_levels(raw: Any) -> list[int]:
        if raw is None:
            return []
        parts = [p.strip() for p in str(raw).split("_")]
        out: list[int] = []
        for p in parts:
            if not p or p in {"-", "--"}:
                continue
            try:
                out.append(int(float(p)))
            except ValueError:
                continue
        return out

    @staticmethod
    def _is_market_open(timestamp: str, *, now: datetime | None = None) -> bool:
        if not timestamp:
            return False
        try:
            t = datetime.strptime(timestamp, "%H:%M:%S").time()
        except ValueError:
            return False
        current = now or datetime.now(ZoneInfo(TAIPEI_TZ))
        if current.tzinfo:
            current_taipei = current.astimezone(ZoneInfo(TAIPEI_TZ))
        else:
            current_taipei = current.replace(tzinfo=ZoneInfo(TAIPEI_TZ))
        if current_taipei.weekday() >= 5:
            return False
        current_tuple = (current_taipei.hour, current_taipei.minute, current_taipei.second)
        quote_tuple = (t.hour, t.minute, t.second)
        market_open = (9, 0, 0)
        market_close = (13, 30, 0)
        return market_open <= current_tuple <= market_close and market_open <= quote_tuple <= market_close
