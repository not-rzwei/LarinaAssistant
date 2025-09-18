import os
import sys

try:
    from loguru import logger as _logger

    def setup_logger(namespace="", log_dir="debug/custom", console_level="INFO"):
        """Setup loguru logger

        Args:
            log_dir: Log file directory
            console_level: Console output level (DEBUG, INFO, WARNING, ERROR)
        """
        os.makedirs(log_dir, exist_ok=True)
        _logger.remove()

        _logger.add(
            sys.stderr,
            format=f"[<level>{{level}}</level>] <level>{{message}}</level>",
            colorize=True,
            level=console_level,
        )

        _logger.add(
            f"{log_dir}/{{time:YYYY-MM-DD}}.log",
            rotation="00:00",  # midnight
            retention="2 weeks",
            compression="zip",
            level="DEBUG",
            format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} | {message}",
            encoding="utf-8",
            enqueue=True,
            backtrace=True,  # Include complete exception traceback
            diagnose=True,  # Include variable value information
        )
        return _logger

    logger = setup_logger()
except ImportError:
    import logging

    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
    )
    logger = logging
