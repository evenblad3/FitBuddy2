import logging
import sys

def setup_logging(debug: bool = True) -> logging.Logger:
    """Configures centralized application logger."""
    level = logging.DEBUG if debug else logging.INFO
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    logging.basicConfig(
        level=level,
        format=log_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )
    logger = logging.getLogger("fitbuddy")
    return logger

logger = setup_logging()
