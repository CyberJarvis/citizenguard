"""
BlueRadar - Advanced Logging System
Multi-handler logging with rotation and formatting
"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
import json
from typing import Optional, Dict, Any

# Color codes for terminal
class Colors:
    RESET = "\033[0m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    WHITE = "\033[97m"
    BOLD = "\033[1m"


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for console output"""
    
    LEVEL_COLORS = {
        logging.DEBUG: Colors.CYAN,
        logging.INFO: Colors.GREEN,
        logging.WARNING: Colors.YELLOW,
        logging.ERROR: Colors.RED,
        logging.CRITICAL: Colors.BOLD + Colors.RED,
    }
    
    def format(self, record):
        # Add color to level name
        color = self.LEVEL_COLORS.get(record.levelno, Colors.WHITE)
        record.levelname = f"{color}{record.levelname:8s}{Colors.RESET}"
        record.name = f"{Colors.BLUE}{record.name}{Colors.RESET}"
        
        return super().format(record)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
            
        if hasattr(record, "extra_data"):
            log_data["data"] = record.extra_data
            
        return json.dumps(log_data)


class BlueRadarLogger:
    """
    Advanced logger with multiple handlers:
    - Console (colored)
    - File (rotating)
    - JSON (structured)
    """
    
    _instances: Dict[str, logging.Logger] = {}
    _log_dir: Optional[Path] = None
    
    @classmethod
    def setup_log_directory(cls, log_dir: Path):
        """Set the log directory"""
        cls._log_dir = Path(log_dir)
        cls._log_dir.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_logger(
        cls,
        name: str,
        level: int = logging.INFO,
        console: bool = True,
        file: bool = True,
        json_log: bool = False
    ) -> logging.Logger:
        """Get or create a logger with specified handlers"""
        
        # Return existing logger if already created
        if name in cls._instances:
            return cls._instances[name]
        
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.handlers = []  # Clear existing handlers
        
        # Console handler (colored)
        if console:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(level)
            console_format = ColoredFormatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_format)
            logger.addHandler(console_handler)
        
        # File handler (rotating)
        if file and cls._log_dir:
            log_file = cls._log_dir / f"{name.replace('.', '_')}.log"
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=5
            )
            file_handler.setLevel(logging.DEBUG)
            file_format = logging.Formatter(
                '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s'
            )
            file_handler.setFormatter(file_format)
            logger.addHandler(file_handler)
        
        # JSON handler (for structured logs)
        if json_log and cls._log_dir:
            json_file = cls._log_dir / f"{name.replace('.', '_')}_json.log"
            json_handler = RotatingFileHandler(
                json_file,
                maxBytes=10 * 1024 * 1024,
                backupCount=3
            )
            json_handler.setLevel(logging.INFO)
            json_handler.setFormatter(JSONFormatter())
            logger.addHandler(json_handler)
        
        cls._instances[name] = logger
        return logger


# Initialize default log directory
try:
    default_log_dir = Path(__file__).parent.parent / "data" / "logs"
    BlueRadarLogger.setup_log_directory(default_log_dir)
except Exception:
    pass


def setup_logging(name: str = "blueradar", level: int = logging.INFO) -> logging.Logger:
    """Convenience function to get a logger"""
    return BlueRadarLogger.get_logger(name, level)


def log_with_data(logger: logging.Logger, level: int, message: str, data: Dict[str, Any]):
    """Log message with additional structured data"""
    record = logger.makeRecord(
        logger.name, level, "", 0, message, (), None
    )
    record.extra_data = data
    logger.handle(record)


# Create default logger
logger = setup_logging("blueradar")
