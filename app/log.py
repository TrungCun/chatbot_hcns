import logging
import sys


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels"""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"
    BOLD = "\033[1m"

    def format(self, record):
        color = self.COLORS.get(record.levelname, self.RESET)

        log_time = self.formatTime(record, "%Y-%m-%d %H:%M:%S")

        log_message = (
            f"{color}{self.BOLD} [{record.levelname}]{self.RESET} "
            f"{color}[{log_time}]{self.RESET} "
            f"{self.BOLD}[{record.name}]{self.RESET} "
            f"→ {record.getMessage()}"
        )

        if record.exc_info:
            log_message += f"\n{self.formatException(record.exc_info)}"

        return log_message


def setup_logging(level=logging.INFO):
    """Setup pretty logging configuration"""

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)

    formatter = ColoredFormatter()
    console_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()
    root_logger.addHandler(console_handler)

    for logger_name in logging.Logger.manager.loggerDict:
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(console_handler)
        logger.propagate = True

    uvicorn_access = logging.getLogger("uvicorn.access")
    uvicorn_access.handlers.clear()
    uvicorn_access.addHandler(console_handler)
    uvicorn_access.propagate = False

    uvicorn_error = logging.getLogger("uvicorn.error")
    uvicorn_error.handlers.clear()
    uvicorn_error.addHandler(console_handler)
    uvicorn_error.propagate = False

    uvicorn_main = logging.getLogger("uvicorn")
    uvicorn_main.handlers.clear()
    uvicorn_main.addHandler(console_handler)
    uvicorn_main.propagate = False

    return root_logger


setup_logging(level=logging.INFO)

get_logger = logging.getLogger
