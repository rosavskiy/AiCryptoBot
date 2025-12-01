"""
Configuration Loader
====================
Loads and validates configuration from YAML and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv


class ConfigLoader:
    """Loads configuration from YAML and environment variables"""
    
    def __init__(self, config_path: str = None):
        """
        Initialize config loader
        
        Args:
            config_path: Path to settings.yaml. If None, uses default path.
        """
        # Load environment variables
        load_dotenv()
        
        # Determine config path
        if config_path is None:
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "settings.yaml"
        
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self._override_with_env()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load YAML configuration file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _override_with_env(self):
        """Override config with environment variables"""
        # Exchange settings
        if os.getenv('BYBIT_TESTNET'):
            self.config['exchange']['testnet'] = os.getenv('BYBIT_TESTNET').lower() == 'true'
        
        # Trading settings
        if os.getenv('DEFAULT_SYMBOL'):
            self.config['symbols'] = [os.getenv('DEFAULT_SYMBOL')]
        
        if os.getenv('DEFAULT_TIMEFRAME'):
            self.config['timeframe']['trading'] = os.getenv('DEFAULT_TIMEFRAME')
        
        # Risk settings
        if os.getenv('RISK_PER_TRADE'):
            self.config['risk']['risk_per_trade'] = float(os.getenv('RISK_PER_TRADE'))
        
        if os.getenv('MAX_POSITIONS'):
            self.config['risk']['max_open_positions'] = int(os.getenv('MAX_POSITIONS'))
        
        # ML settings
        if os.getenv('ML_CONFIDENCE_THRESHOLD'):
            self.config['ml']['confidence_threshold'] = float(os.getenv('ML_CONFIDENCE_THRESHOLD'))
        
        # Sentiment settings
        if os.getenv('SENTIMENT_THRESHOLD'):
            self.config['sentiment']['min_score'] = float(os.getenv('SENTIMENT_THRESHOLD'))
    
    def get(self, *keys: str, default=None) -> Any:
        """
        Get configuration value by nested keys
        
        Example:
            config.get('risk', 'risk_per_trade')
            config.get('ml', 'confidence_threshold')
        """
        value = self.config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value
    
    def get_api_credentials(self) -> Dict[str, str]:
        """Get API credentials from environment"""
        return {
            'api_key': os.getenv('BYBIT_API_KEY', ''),
            'api_secret': os.getenv('BYBIT_API_SECRET', ''),
            'testnet': os.getenv('BYBIT_TESTNET', 'True').lower() == 'true'
        }
    
    def __repr__(self) -> str:
        return f"<ConfigLoader: {self.config_path}>"


# Global config instance
_config = None

def get_config(config_path: str = None) -> ConfigLoader:
    """Get global config instance (singleton pattern)"""
    global _config
    if _config is None:
        _config = ConfigLoader(config_path)
    return _config
