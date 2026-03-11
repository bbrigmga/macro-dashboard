"""
Enhanced Logging Configuration for Volatility Components

Provides structured logging with different levels and handlers for production monitoring.
Supports file logging, console output, and performance tracking.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional


class VolatilityLoggerConfig:
    """
    Configuration class for enhanced logging across volatility components.
    Sets up structured logging with appropriate levels and handlers.
    """
    
    def __init__(
        self, 
        log_level: str = "INFO",
        log_to_file: bool = True,
        log_to_console: bool = True,
        log_directory: str = "logs",
        max_bytes: int = 10 * 1024 * 1024,  # 10MB
        backup_count: int = 5
    ):
        """
        Initialize logging configuration.
        
        Args:
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_to_file: Whether to log to files
            log_to_console: Whether to log to console
            log_directory: Directory for log files
            max_bytes: Maximum log file size before rotation
            backup_count: Number of backup files to keep
        """
        self.log_level = getattr(logging, log_level.upper())
        self.log_to_file = log_to_file
        self.log_to_console = log_to_console
        self.log_directory = Path(log_directory)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        
        # Create logs directory
        if self.log_to_file:
            self.log_directory.mkdir(parents=True, exist_ok=True)
    
    def setup_logger(self, name: str) -> logging.Logger:
        """
        Set up a logger with the configured handlers.
        
        Args:
            name: Logger name (typically __name__)
            
        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(name)
        
        # Avoid duplicate handlers if logger already configured
        if logger.handlers:
            return logger
            
        logger.setLevel(self.log_level)
        
        # Create formatters
        detailed_formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        simple_formatter = logging.Formatter(
            fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
            datefmt='%H:%M:%S'
        )
        
        # Console handler
        if self.log_to_console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(self.log_level)
            console_handler.setFormatter(simple_formatter)
            logger.addHandler(console_handler)
        
        # File handlers
        if self.log_to_file:
            # General application log
            general_log_path = self.log_directory / f"{name.replace('.', '_')}.log"
            file_handler = logging.handlers.RotatingFileHandler(
                general_log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            file_handler.setFormatter(detailed_formatter)
            logger.addHandler(file_handler)
            
            # Error-only log for critical issues
            error_log_path = self.log_directory / f"{name.replace('.', '_')}_errors.log"
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(detailed_formatter)
            logger.addHandler(error_handler)
        
        return logger
    
    def setup_performance_logger(self) -> logging.Logger:
        """
        Set up a dedicated performance logger for timing and metrics.
        
        Returns:
            Performance logger instance
        """
        perf_logger = logging.getLogger("volatility.performance")
        
        if perf_logger.handlers:
            return perf_logger
            
        perf_logger.setLevel(logging.INFO)
        
        # Performance log format
        perf_formatter = logging.Formatter(
            fmt='%(asctime)s - PERF - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        if self.log_to_file:
            perf_log_path = self.log_directory / "volatility_performance.log"
            perf_handler = logging.handlers.RotatingFileHandler(
                perf_log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            perf_handler.setLevel(logging.INFO)
            perf_handler.setFormatter(perf_formatter)
            perf_logger.addHandler(perf_handler)
        
        if self.log_to_console:
            console_perf_handler = logging.StreamHandler(sys.stdout)
            console_perf_handler.setLevel(logging.INFO)
            console_perf_handler.setFormatter(perf_formatter)
            perf_logger.addHandler(console_perf_handler)
        
        return perf_logger
    
    def setup_data_quality_logger(self) -> logging.Logger:
        """
        Set up a dedicated logger for data quality metrics and issues.
        
        Returns:
            Data quality logger instance
        """
        quality_logger = logging.getLogger("volatility.data_quality")
        
        if quality_logger.handlers:
            return quality_logger
            
        quality_logger.setLevel(logging.INFO)
        
        # Quality log format
        quality_formatter = logging.Formatter(
            fmt='%(asctime)s - QUALITY - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        if self.log_to_file:
            quality_log_path = self.log_directory / "volatility_data_quality.log"
            quality_handler = logging.handlers.RotatingFileHandler(
                quality_log_path,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count
            )
            quality_handler.setLevel(logging.INFO)
            quality_handler.setFormatter(quality_formatter)
            quality_logger.addHandler(quality_handler)
        
        if self.log_to_console and self.log_level <= logging.DEBUG:
            console_quality_handler = logging.StreamHandler(sys.stdout)
            console_quality_handler.setLevel(logging.INFO)
            console_quality_handler.setFormatter(quality_formatter)
            quality_logger.addHandler(console_quality_handler)
        
        return quality_logger


# Global logger configuration instance
_logger_config = None

def get_logger_config() -> VolatilityLoggerConfig:
    """Get the global logger configuration instance."""
    global _logger_config
    if _logger_config is None:
        # Configure based on environment variables
        log_level = os.environ.get("LOG_LEVEL", "INFO")
        log_to_file = os.environ.get("LOG_TO_FILE", "true").lower() == "true"
        log_to_console = os.environ.get("LOG_TO_CONSOLE", "true").lower() == "true"
        
        _logger_config = VolatilityLoggerConfig(
            log_level=log_level,
            log_to_file=log_to_file,
            log_to_console=log_to_console
        )
    return _logger_config

def get_volatility_logger(name: str) -> logging.Logger:
    """
    Get a configured logger for volatility components.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    """
    config = get_logger_config()
    return config.setup_logger(name)

def get_performance_logger() -> logging.Logger:
    """Get the performance logger for timing and metrics."""
    config = get_logger_config()
    return config.setup_performance_logger()

def get_data_quality_logger() -> logging.Logger:
    """Get the data quality logger for quality metrics and issues."""
    config = get_logger_config()
    return config.setup_data_quality_logger()

def log_performance_metric(metric_name: str, value: float, unit: str = "", context: dict | None = None):
    """
    Log a performance metric in a structured format.
    
    Args:
        metric_name: Name of the metric (e.g., "database_query_time")
        value: Metric value
        unit: Unit of measurement (e.g., "ms", "seconds", "count")
        context: Additional context dictionary
    """
    perf_logger = get_performance_logger()
    
    context_str = ""
    if context:
        context_items = [f"{k}={v}" for k, v in context.items()]
        context_str = f" | {' | '.join(context_items)}"
    
    perf_logger.info(f"{metric_name}: {value:.4f} {unit}{context_str}")

def log_data_quality_metric(metric_name: str, value: float, threshold: float | None = None, ticker: str | None = None):
    """
    Log a data quality metric in a structured format.
    
    Args:
        metric_name: Name of the quality metric (e.g., "iv_data_quality_score")
        value: Quality metric value
        threshold: Quality threshold for warnings
        ticker: Associated ticker symbol
    """
    quality_logger = get_data_quality_logger()
    
    ticker_str = f" | ticker={ticker}" if ticker else ""
    
    if threshold is not None:
        quality_status = "GOOD" if value >= threshold else "POOR"
        quality_logger.info(f"{metric_name}: {value:.2f} | status={quality_status}{ticker_str}")
        
        if value < threshold:
            quality_logger.warning(f"Data quality below threshold for {metric_name}: {value:.2f} < {threshold}")
    else:
        quality_logger.info(f"{metric_name}: {value:.2f}{ticker_str}")

def setup_volatility_logging():
    """
    Initialize logging configuration for all volatility components.
    Call this once at application startup.
    """
    config = get_logger_config()
    
    # Set up root volatility logger
    root_logger = config.setup_logger("volatility")
    root_logger.info("Volatility logging system initialized")
    
    # Set up specialized loggers
    config.setup_performance_logger()
    config.setup_data_quality_logger()
    
    # Log configuration details
    root_logger.info(f"Log level: {logging.getLevelName(config.log_level)}")
    root_logger.info(f"Log to file: {config.log_to_file}")
    root_logger.info(f"Log to console: {config.log_to_console}")
    if config.log_to_file:
        root_logger.info(f"Log directory: {config.log_directory.absolute()}")
    
    return root_logger