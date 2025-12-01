"""
Market Type Configuration
==========================
Handles SPOT vs FUTURES trading configuration
"""

import logging
import os
from typing import Dict, Optional
import ccxt

logger = logging.getLogger(__name__)


class MarketTypeManager:
    """
    Manages market type configuration (SPOT vs FUTURES)
    """
    
    SPOT = 'spot'
    FUTURES = 'futures'
    LINEAR = 'linear'  # USDT-margined futures
    INVERSE = 'inverse'  # Coin-margined futures
    
    def __init__(self, market_type: str = None):
        """
        Initialize market type manager
        
        Args:
            market_type: 'spot', 'futures', 'linear', or 'inverse'
        """
        self.market_type = (market_type or os.getenv('MARKET_TYPE', 'spot')).lower()
        
        if self.market_type not in [self.SPOT, self.FUTURES, self.LINEAR, self.INVERSE]:
            logger.warning(f'Invalid market type: {self.market_type}. Defaulting to SPOT')
            self.market_type = self.SPOT
        
        # Normalize futures types
        if self.market_type in [self.FUTURES, self.LINEAR]:
            self.market_type = self.LINEAR
        
        logger.info(f'[MARKET] Type: {self.market_type.upper()}')
    
    def is_spot(self) -> bool:
        """Check if trading on SPOT"""
        return self.market_type == self.SPOT
    
    def is_futures(self) -> bool:
        """Check if trading on FUTURES"""
        return self.market_type in [self.FUTURES, self.LINEAR, self.INVERSE]
    
    def is_linear(self) -> bool:
        """Check if using linear (USDT-margined) futures"""
        return self.market_type == self.LINEAR
    
    def is_inverse(self) -> bool:
        """Check if using inverse (coin-margined) futures"""
        return self.market_type == self.INVERSE
    
    def get_market_id(self, symbol: str) -> str:
        """
        Convert symbol to exchange-specific market ID
        
        Args:
            symbol: Standard symbol like 'BTC/USDT'
            
        Returns:
            Market ID for the exchange
        """
        if self.is_spot():
            return symbol
        
        # For futures, Bybit uses different formats
        if self.is_linear():
            # Linear futures: BTC/USDT:USDT or BTCUSDT
            base, quote = symbol.split('/')
            return f'{base}{quote}'  # BTCUSDT for linear perpetuals
        
        if self.is_inverse():
            # Inverse futures: BTC/USD:BTC
            base = symbol.split('/')[0]
            return f'{base}USD'  # BTCUSD for inverse perpetuals
        
        return symbol
    
    def configure_exchange(self, exchange: ccxt.Exchange) -> ccxt.Exchange:
        """
        Configure exchange for the selected market type
        
        Args:
            exchange: CCXT exchange instance
            
        Returns:
            Configured exchange
        """
        try:
            if self.is_futures():
                # Set options for futures trading
                exchange.options['defaultType'] = 'future'
                
                if hasattr(exchange, 'set_margin_mode'):
                    # Set isolated margin for safety
                    exchange.set_margin_mode('isolated')
                    logger.info('[MARKET] ✅ Margin mode: ISOLATED')
                
                if self.is_linear():
                    exchange.options['defaultSettle'] = 'USDT'
                    logger.info('[MARKET] ✅ Futures: USDT-margined (Linear)')
                else:
                    exchange.options['defaultSettle'] = 'BTC'
                    logger.info('[MARKET] ✅ Futures: Coin-margined (Inverse)')
            else:
                # SPOT trading
                exchange.options['defaultType'] = 'spot'
                logger.info('[MARKET] ✅ Trading mode: SPOT')
            
            return exchange
            
        except Exception as e:
            logger.error(f'[MARKET] ❌ Error configuring exchange: {e}')
            return exchange
    
    def get_position_size_params(self, 
                                  symbol: str,
                                  size: float,
                                  side: str) -> Dict:
        """
        Get parameters for position sizing based on market type
        
        Args:
            symbol: Trading symbol
            size: Position size
            side: 'buy' or 'sell'
            
        Returns:
            Dictionary with exchange-specific parameters
        """
        params = {}
        
        if self.is_futures():
            # Futures-specific parameters
            params['position_side'] = 'LONG' if side == 'buy' else 'SHORT'
            params['reduce_only'] = False
            
            if self.is_linear():
                # For linear futures, size is in base currency (BTC)
                params['type'] = 'market'
            else:
                # For inverse futures, contracts calculation
                params['type'] = 'market'
        
        return params
    
    def calculate_pnl(self,
                      entry_price: float,
                      current_price: float,
                      size: float,
                      side: str) -> float:
        """
        Calculate P&L based on market type
        
        Args:
            entry_price: Entry price
            current_price: Current price
            size: Position size
            side: 'long' or 'short'
            
        Returns:
            P&L in quote currency (USDT)
        """
        if self.is_spot():
            # SPOT P&L
            if side.lower() == 'long':
                return (current_price - entry_price) * size
            else:
                # SPOT doesn't support short
                return 0.0
        
        if self.is_linear():
            # Linear futures P&L (USDT-margined)
            if side.lower() == 'long':
                pnl = (current_price - entry_price) * size
            else:
                pnl = (entry_price - current_price) * size
            return pnl
        
        if self.is_inverse():
            # Inverse futures P&L (coin-margined)
            # P&L = size * (1/entry_price - 1/current_price)
            if side.lower() == 'long':
                pnl = size * (1/entry_price - 1/current_price)
            else:
                pnl = size * (1/current_price - 1/entry_price)
            
            # Convert to USDT
            return pnl * current_price
        
        return 0.0
    
    def get_leverage_info(self) -> Dict:
        """Get leverage information"""
        if self.is_spot():
            return {
                'available': False,
                'max_leverage': 1,
                'current_leverage': 1
            }
        
        return {
            'available': True,
            'max_leverage': 100 if self.is_linear() else 100,
            'current_leverage': int(os.getenv('LEVERAGE', '1')),
            'recommended': 3,  # Conservative recommendation
            'warning': 'Higher leverage = higher risk!'
        }
    
    def get_market_info(self) -> Dict:
        """Get market type information"""
        return {
            'type': self.market_type,
            'is_spot': self.is_spot(),
            'is_futures': self.is_futures(),
            'is_linear': self.is_linear(),
            'is_inverse': self.is_inverse(),
            'leverage': self.get_leverage_info(),
            'description': self._get_description()
        }
    
    def _get_description(self) -> str:
        """Get human-readable description"""
        if self.is_spot():
            return 'SPOT - Buy and hold physical crypto'
        if self.is_linear():
            return 'LINEAR FUTURES - USDT-margined perpetual contracts with leverage'
        if self.is_inverse():
            return 'INVERSE FUTURES - Coin-margined perpetual contracts'
        return 'Unknown market type'


# Global instance
_market_manager = None

def get_market_manager() -> MarketTypeManager:
    """Get global market type manager instance"""
    global _market_manager
    if _market_manager is None:
        _market_manager = MarketTypeManager()
    return _market_manager


def configure_exchange_for_market(exchange: ccxt.Exchange) -> ccxt.Exchange:
    """Helper function to configure exchange"""
    manager = get_market_manager()
    return manager.configure_exchange(exchange)


if __name__ == '__main__':
    # Test market type manager
    import os
    
    logging.basicConfig(level=logging.INFO)
    
    print("\n=== SPOT Trading ===")
    os.environ['MARKET_TYPE'] = 'spot'
    manager = MarketTypeManager()
    print(manager.get_market_info())
    print(f"Market ID: {manager.get_market_id('BTC/USDT')}")
    
    print("\n=== LINEAR FUTURES Trading ===")
    os.environ['MARKET_TYPE'] = 'futures'
    manager = MarketTypeManager('linear')
    print(manager.get_market_info())
    print(f"Market ID: {manager.get_market_id('BTC/USDT')}")
    
    print("\n=== P&L Calculation ===")
    # LONG position: bought at 90000, now at 95000, size 0.1 BTC
    pnl = manager.calculate_pnl(90000, 95000, 0.1, 'long')
    print(f"LONG P&L: ${pnl:.2f}")
    
    # SHORT position: sold at 95000, now at 90000, size 0.1 BTC
    pnl = manager.calculate_pnl(95000, 90000, 0.1, 'short')
    print(f"SHORT P&L: ${pnl:.2f}")
