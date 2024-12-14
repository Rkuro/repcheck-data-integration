from logging import config
import sys

def setup_logging():
    """Set up consistent logging configuration for the entire project."""
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": sys.stdout,
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
    config.dictConfig(logging_config)

