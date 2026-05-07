"""Example strategies."""

from src.strategy.examples.bias import BiasStrategy
from src.strategy.examples.bollinger_band import BollingerBandStrategy
from src.strategy.examples.dca import DollarCostAveragingStrategy
from src.strategy.examples.donchian_breakout import DonchianBreakoutStrategy
from src.strategy.examples.kd_cross import KDCrossStrategy
from src.strategy.examples.ma_cross import MACrossStrategy
from src.strategy.examples.macd_cross import MACDCrossStrategy
from src.strategy.examples.rsi import RSIStrategy

__all__ = [
    "MACrossStrategy",
    "DollarCostAveragingStrategy",
    "RSIStrategy",
    "KDCrossStrategy",
    "MACDCrossStrategy",
    "BollingerBandStrategy",
    "BiasStrategy",
    "DonchianBreakoutStrategy",
]
