"""Chart theme and cache knobs used by the dashboard."""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class CacheConfig:
    enabled: bool = True
    max_memory_size: int = 512
    default_ttl: int = 3600  # 1 hour


@dataclass
class ChartConfig:
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
        },
        'colorscale': [[0, '#f44336'], [0.5, '#ff9800'], [1, '#00c853']]
    })
    default_periods: int = 36


@dataclass
class Settings:
    cache: CacheConfig = field(default_factory=CacheConfig)
    chart: ChartConfig = field(default_factory=ChartConfig)


settings = Settings()


def get_settings() -> Settings:
    return settings
