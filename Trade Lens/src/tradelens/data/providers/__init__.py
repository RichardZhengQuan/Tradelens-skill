"""Optional market data providers for Trade Lens."""

from tradelens.data.provider_base import MarketDataProvider
from tradelens.data.providers.cnn_fear_greed_provider import CNNFearGreedProvider
from tradelens.data.providers.finnhub_provider import FinnhubProvider
from tradelens.data.providers.futu_provider import FutuProvider
from tradelens.data.providers.futu_opend_provider import FutuOpenDProvider
from tradelens.data.providers.manual_provider import ManualMarketDataProvider
from tradelens.data.providers.moomoo_opend_provider import MoomooOpenDProvider
from tradelens.data.providers.optioncharts_provider import OptionChartsProvider
from tradelens.data.providers.opend_base_provider import OpenDProvider
from tradelens.data.providers.polygon_provider import PolygonProvider
from tradelens.data.providers.tradier_provider import TradierProvider
from tradelens.data.providers.yahoo_provider import YahooProvider

__all__ = [
    "CNNFearGreedProvider",
    "FinnhubProvider",
    "FutuProvider",
    "FutuOpenDProvider",
    "ManualMarketDataProvider",
    "MarketDataProvider",
    "MoomooOpenDProvider",
    "OpenDProvider",
    "OptionChartsProvider",
    "PolygonProvider",
    "TradierProvider",
    "YahooProvider",
]
