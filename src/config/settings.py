"""
Configuration management for Macro Dashboard.
Centralized settings for API keys, caching, chart parameters, and more.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from pathlib import Path


@dataclass
class APIConfig:
    """API-related configuration settings."""

    fred_api_key: Optional[str] = None
    fred_base_url: str = "https://api.stlouisfed.org/fred"
    request_timeout: int = 30
    max_retries: int = 3
    backoff_factor: int = 2

    def __post_init__(self):
        if self.fred_api_key is None:
            self.fred_api_key = os.getenv('FRED_API_KEY')


@dataclass
class CacheConfig:
    """Caching configuration settings."""

    enabled: bool = True
    max_memory_size: int = 512
    disk_cache_dir: str = "data/cache"
    default_ttl: int = 3600  # 1 hour
    fred_ttl: int = 86400  # 24 hours for FRED data
    yahoo_ttl: int = 3600  # 1 hour for Yahoo data


@dataclass
class ChartConfig:
    """Chart and visualization configuration."""

    default_height: int = 250
    default_width: int = 800
    theme_colors: Dict[str, Any] = field(default_factory=lambda: {
        'background': '#f5f7fa',
        'paper_bgcolor': '#ffffff',
        'font_color': '#333333',
        'grid_color': 'rgba(0, 0, 0, 0.1)',
        'line_colors': {
            'primary': '#1a7fe0',
            'success': '#00c853',
            'warning': '#ff9800',
            'danger': '#f44336',
            'neutral': '#78909c'
        }
    })
    default_periods: int = 36


@dataclass
class DataConfig:
    """Data processing configuration."""

    usd_liquidity_components: Dict[str, str] = field(default_factory=lambda: {
        'fed_balance': 'WALCL',
        'reverse_repo': 'RRPONTTLD',
        'treasury_account': 'WTREGEN',
        'currency_circulation': 'CURRCIR',
        'gdp': 'GDPC1',
        'tariff_receipts': 'B235RC1Q027SBEA'
    })

    pmi_components: Dict[str, str] = field(default_factory=lambda: {
        'new_orders': 'AMTMNO',
        'production': 'IPMAN',
        'employment': 'MANEMP',
        'supplier_deliveries': 'AMDMUS',
        'inventories': 'MNFCTRIMSA'
    })

    pmi_weights: Dict[str, float] = field(default_factory=lambda: {
        'new_orders': 0.30,
        'production': 0.25,
        'employment': 0.20,
        'supplier_deliveries': 0.15,
        'inventories': 0.10
    })


@dataclass
class LoggingConfig:
    """Logging configuration."""

    level: str = "INFO"
    format: str = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    file_path: Optional[str] = None


@dataclass
class Settings:
    """Main application settings."""

    # Core configurations
    api: APIConfig = field(default_factory=APIConfig)
    cache: CacheConfig = field(default_factory=CacheConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)
    data: DataConfig = field(default_factory=DataConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    # Environment and debug settings
    debug: bool = False
    environment: str = "development"

    def __post_init__(self):
        """Post-initialization setup."""
        # Set debug mode from environment
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.environment = os.getenv('ENVIRONMENT', 'development')

        # Set logging level based on debug mode
        if self.debug:
            self.logging.level = "DEBUG"

        # Ensure cache directory exists
        cache_dir = Path(self.cache.disk_cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()


def get_settings() -> Settings:
    """Get the global settings instance."""
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment variables."""
    global settings
    settings = Settings()
    return settings