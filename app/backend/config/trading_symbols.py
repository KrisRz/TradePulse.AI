"""
Trading Symbol Standardization for TradePulse.AI
Centralizes symbol mapping and ensures consistent usage across all services
"""

from typing import Dict, Set
import logging

logger = logging.getLogger(__name__)


class TradingSymbols:
    """Centralized trading symbol management"""
    
    # Primary symbols used throughout the application
    CANONICAL_SYMBOL = "BTCUSDT"  # Main symbol for all internal processing
    
    # Symbol mappings from various sources to canonical symbol
    SYMBOL_MAPPINGS = {
        # Binance WebSocket variations
        "BTCUSD": "BTCUSDT",
        "btcusd": "BTCUSDT", 
        "btcusdt": "BTCUSDT",
        "BTC-USD": "BTCUSDT",
        "BTC/USD": "BTCUSDT",
        "BTC_USD": "BTCUSDT",
        
        # Standard forms
        "BTCUSDT": "BTCUSDT",  # Already canonical
        
        # Other common variations
        "Bitcoin": "BTCUSDT",
        "bitcoin": "BTCUSDT",
        "BTC": "BTCUSDT"
    }
    
    # Supported symbols (for future expansion)
    SUPPORTED_SYMBOLS = {
        "BTCUSDT": {
            "name": "Bitcoin",
            "base_asset": "BTC",
            "quote_asset": "USDT",
            "binance_stream": "btcusdt",
            "binance_ticker": "btcusdt@ticker",
            "binance_kline": "btcusdt@kline_1m"
        }
    }
    
    @classmethod
    def normalize_symbol(cls, symbol: str) -> str:
        """
        Normalize any symbol variation to canonical form
        
        Args:
            symbol: Input symbol in any format
            
        Returns:
            str: Canonical symbol (BTCUSDT)
        """
        if not symbol:
            logger.warning("Empty symbol provided, using default BTCUSDT")
            return cls.CANONICAL_SYMBOL
            
        # Clean the input
        symbol_clean = symbol.strip().upper()
        
        # Check direct mapping
        if symbol_clean in cls.SYMBOL_MAPPINGS:
            canonical = cls.SYMBOL_MAPPINGS[symbol_clean]
            if symbol_clean != canonical:
                logger.debug(f"Symbol normalized: {symbol} → {canonical}")
            return canonical
        
        # If no mapping found, log warning and return canonical
        logger.warning(f"Unknown symbol '{symbol}', using canonical {cls.CANONICAL_SYMBOL}")
        return cls.CANONICAL_SYMBOL
    
    @classmethod
    def get_binance_stream_symbol(cls, symbol: str = None) -> str:
        """
        Get Binance WebSocket stream symbol format
        
        Args:
            symbol: Input symbol (optional, defaults to canonical)
            
        Returns:
            str: Lowercase symbol for Binance streams (btcusdt)
        """
        canonical = cls.normalize_symbol(symbol) if symbol else cls.CANONICAL_SYMBOL
        symbol_info = cls.SUPPORTED_SYMBOLS.get(canonical, {})
        return symbol_info.get("binance_stream", "btcusdt")
    
    @classmethod
    def get_binance_ticker_stream(cls, symbol: str = None) -> str:
        """
        Get Binance ticker stream name
        
        Args:
            symbol: Input symbol (optional, defaults to canonical)
            
        Returns:
            str: Binance ticker stream name (btcusdt@ticker)
        """
        canonical = cls.normalize_symbol(symbol) if symbol else cls.CANONICAL_SYMBOL
        symbol_info = cls.SUPPORTED_SYMBOLS.get(canonical, {})
        return symbol_info.get("binance_ticker", "btcusdt@ticker")
    
    @classmethod
    def get_binance_kline_stream(cls, symbol: str = None, interval: str = "1m") -> str:
        """
        Get Binance kline stream name
        
        Args:
            symbol: Input symbol (optional, defaults to canonical)
            interval: Kline interval (1m, 5m, etc.)
            
        Returns:
            str: Binance kline stream name (btcusdt@kline_1m)
        """
        stream_symbol = cls.get_binance_stream_symbol(symbol)
        return f"{stream_symbol}@kline_{interval}"
    
    @classmethod
    def is_supported(cls, symbol: str) -> bool:
        """
        Check if symbol is supported
        
        Args:
            symbol: Symbol to check
            
        Returns:
            bool: True if supported
        """
        canonical = cls.normalize_symbol(symbol)
        return canonical in cls.SUPPORTED_SYMBOLS
    
    @classmethod
    def get_symbol_info(cls, symbol: str = None) -> Dict[str, str]:
        """
        Get detailed symbol information
        
        Args:
            symbol: Input symbol (optional, defaults to canonical)
            
        Returns:
            Dict: Symbol information
        """
        canonical = cls.normalize_symbol(symbol) if symbol else cls.CANONICAL_SYMBOL
        return cls.SUPPORTED_SYMBOLS.get(canonical, {})
    
    @classmethod
    def validate_and_log_symbol_usage(cls, symbol: str, context: str = "") -> str:
        """
        Validate symbol and log any normalization for debugging
        
        Args:
            symbol: Input symbol
            context: Context for logging (e.g., "WebSocket", "REST API")
            
        Returns:
            str: Canonical symbol
        """
        original_symbol = symbol
        canonical = cls.normalize_symbol(symbol)
        
        if original_symbol != canonical:
            logger.info(f"🔄 Symbol normalized in {context}: {original_symbol} → {canonical}")
        
        return canonical


# Global instance for easy access
symbols = TradingSymbols()


# Convenience functions
def normalize_symbol(symbol: str) -> str:
    """Convenience function to normalize symbol"""
    return symbols.normalize_symbol(symbol)


def get_canonical_symbol() -> str:
    """Get the canonical symbol used throughout the application"""
    return TradingSymbols.CANONICAL_SYMBOL


def get_binance_streams(symbol: str = None) -> Dict[str, str]:
    """Get all Binance stream names for a symbol"""
    return {
        "ticker": symbols.get_binance_ticker_stream(symbol),
        "kline_1m": symbols.get_binance_kline_stream(symbol, "1m"),
        "kline_5m": symbols.get_binance_kline_stream(symbol, "5m"),
        "stream_symbol": symbols.get_binance_stream_symbol(symbol)
    }


def log_symbol_mapping_stats():
    """Log symbol mapping statistics for debugging"""
    logger.info("🎯 SYMBOL MAPPING CONFIGURATION:")
    logger.info(f"   Canonical symbol: {TradingSymbols.CANONICAL_SYMBOL}")
    logger.info(f"   Supported symbols: {len(TradingSymbols.SUPPORTED_SYMBOLS)}")
    logger.info(f"   Mapped variations: {len(TradingSymbols.SYMBOL_MAPPINGS)}")
    
    for original, canonical in TradingSymbols.SYMBOL_MAPPINGS.items():
        if original != canonical:
            logger.debug(f"   {original} → {canonical}")
