import logging
import sys

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure application-wide logging.

    Why centralized:
    - Avoids duplicate logger configuration
    - Ensures consistent log format
    - Makes log level environment-aware
    """

    log_level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        level=log_level,
        format=(
            "%(asctime)s | "
            "%(levelname)s | "
            "%(name)s | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ],
    )
