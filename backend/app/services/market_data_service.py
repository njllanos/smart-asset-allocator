"""
Servicio de datos de mercado. 
Encapsula la lógica de yfinance con caching y manejo de errores.
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

import numpy as np
import pandas as pd
import yfinance as yf

from ..config import get_settings
from ..core.exceptions import (
    MarketDataException, 
    InvalidTickerException,
    InsufficientDataException
)
from ..models.schemas import AssetStatistics, MarketDataResponse
from ..models.enums import TimeframePreset
from ..core.cache import cache_response  # Asegúrate de haber creado este archivo

logger = logging.getLogger(__name__)
settings = get_settings()


class MarketDataService:
    """
    Servicio para obtención y procesamiento de datos de mercado. 
    Implementa caching y cálculos financieros estándar.
    """
    
    TIMEFRAME_MAPPING = {
        TimeframePreset.ONE_YEAR: 365,
        TimeframePreset.THREE_YEARS: 365 * 3,
        TimeframePreset.FIVE_YEARS: 365 * 5,
        TimeframePreset.MAX: 365 * 10,
    }
    
    def __init__(self):
        self.trading_days = settings.TRADING_DAYS_PER_YEAR
    
    @cache_response  # ✅ Decorador aplicado correctamente
    async def get_market_data(
        self, 
        tickers: List[str], 
        timeframe: TimeframePreset = TimeframePreset.THREE_YEARS
    ) -> MarketDataResponse:
        """
        Obtiene datos de mercado y calcula métricas para múltiples activos.
        """
        logger.info(f"Fetching market data for {len(tickers)} tickers: {tickers}")
        
        # Calcular fechas
        days = self.TIMEFRAME_MAPPING[timeframe]
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # Descargar datos
        try: 
            prices_df = self._download_prices(tickers, start_date, end_date)
        except Exception as e:
            logger.error(f"Error downloading prices: {e}")
            raise MarketDataException(f"Error obteniendo precios: {str(e)}")
        
        # Validar datos suficientes
        self._validate_data_sufficiency(prices_df, tickers)
        
        # Calcular retornos logarítmicos
        log_returns = self._calculate_log_returns(prices_df)
        
        # Calcular matrices
        cov_matrix = self._calculate_covariance_matrix(log_returns)
        corr_matrix = log_returns.corr()
        
        # Calcular estadísticas por activo
        statistics = {}
        for ticker in tickers: 
            if ticker in log_returns.columns:
                statistics[ticker] = self._calculate_asset_statistics(
                    ticker, 
                    prices_df[ticker], 
                    log_returns[ticker]
                )
        
        # Preparar sample de retornos (últimos 30 días)
        returns_sample = {
            ticker: log_returns[ticker].tail(30).tolist()
            for ticker in log_returns.columns
        }
        
        return MarketDataResponse(
            tickers=list(statistics.keys()),
            statistics=statistics,
            covariance_matrix=cov_matrix.to_dict(),
            correlation_matrix=corr_matrix.to_dict(),
            log_returns_sample=returns_sample,
            data_start_date=prices_df.index.min().date(),
            data_end_date=prices_df.index.max().date(),
            trading_days=len(prices_df)
        )
    
    def _download_prices(
        self, 
        tickers: List[str], 
        start_date: datetime, 
        end_date: datetime
    ) -> pd.DataFrame:
        """Descarga precios ajustados de Yahoo Finance."""
        try:
            data = yf.download(
                tickers=tickers,
                start=start_date,
                end=end_date,
                progress=False,
                auto_adjust=True,
                threads=True
            )
            
            if isinstance(data.columns, pd.MultiIndex):
                prices = data['Close']
            else:
                prices = data[['Close']].rename(columns={'Close': tickers[0]})
            
            prices = prices.dropna(how='all')
            
            if prices.empty:
                raise MarketDataException("No se obtuvieron datos de precios")
            
            return prices
            
        except Exception as e:
            logger.exception(f"yfinance download error: {e}")
            raise

    def _validate_data_sufficiency(self, prices_df, tickers, min_days=245):
        invalid_tickers = []
        for ticker in tickers:
            if ticker not in prices_df.columns:
                invalid_tickers.append(ticker)
            elif prices_df[ticker].dropna().shape[0] < min_days:
                raise InsufficientDataException(ticker, min_days, prices_df[ticker].dropna().shape[0])
        if invalid_tickers:
            raise InvalidTickerException(", ".join(invalid_tickers))

    def _calculate_log_returns(self, prices):
        return np.log(prices / prices.shift(1)).dropna()

    def _calculate_covariance_matrix(self, log_returns, annualize=True):
        cov = log_returns.cov()
        if annualize:
            cov = cov * self.trading_days
        return cov

    def _calculate_asset_statistics(self, ticker, prices, log_returns):
        mean_daily_return = log_returns.mean()
        daily_volatility = log_returns.std()
        
        annualized_return = mean_daily_return * self.trading_days
        annualized_volatility = daily_volatility * np.sqrt(self.trading_days)
        
        sharpe_ratio = (annualized_return / annualized_volatility) if annualized_volatility > 0 else 0
        
        cumulative = (1 + log_returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdowns = (cumulative - rolling_max) / rolling_max
        max_drawdown = drawdowns.min()
        
        last_price = prices.dropna().iloc[-1]
        
        price_change_1y = None
        if len(prices.dropna()) > self.trading_days:
            price_1y_ago = prices.dropna().iloc[-self.trading_days]
            price_change_1y = (last_price - price_1y_ago) / price_1y_ago
        
        return AssetStatistics(
            ticker=ticker,
            annualized_return=round(annualized_return * 100, 2),
            annualized_volatility=round(annualized_volatility * 100, 2),
            sharpe_ratio=round(sharpe_ratio, 3),
            max_drawdown=round(max_drawdown * 100, 2),
            last_price=round(last_price, 2),
            price_change_1y=round(price_change_1y * 100, 2) if price_change_1y else None
        )
    
    async def get_log_returns_dataframe(self, tickers, timeframe=TimeframePreset.THREE_YEARS):
        days = self.TIMEFRAME_MAPPING[timeframe]
        start_date = datetime.now() - timedelta(days=days)
        prices_df = self._download_prices(tickers, start_date, datetime.now())
        return self._calculate_log_returns(prices_df)