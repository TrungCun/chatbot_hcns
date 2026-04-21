import logging
import sys

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""

    # ANSI color codes
    COLORS = {
        "DEBUG": "\033[36m",     # Cyan
        "INFO": "\033[32m",      # Green
        "WARNING": "\033[33m",   # Yellow
        "ERROR": "\033[31m",     # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"
    TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)
        log_time = self.formatTime(record, self.TIME_FORMAT)
        msg = record.getMessage()

        # Build colored log message
        level_part = f"{color}{self.BOLD}[{record.levelname}]{self.RESET}"
        time_part = f"{color}[{log_time}]{self.RESET}"
        name_part = f"{self.BOLD}[{record.name}]{self.RESET}"

        log_message = f"{level_part} {time_part} {name_part} → {msg}"

        # Append exception traceback if present
        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


def setup_logging(level=logging.INFO):
    """Setup pretty logging configuration"""

    # Create handler & formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(ColoredFormatter())

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    # Configure uvicorn loggers to suppress duplicate messages
    for logger_name in ("uvicorn.access", "uvicorn.error", "uvicorn"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.propagate = False

    return root_logger


# Initialize logging on module import
setup_logging(level=logging.INFO)

# Convenience function for getting loggers
get_logger = logging.getLogger
