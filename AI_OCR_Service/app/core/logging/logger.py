import sys
import os
import logging
from loguru import logger

# Set Python to use UTF-8 for stdout on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Intercept standard library logging and route to Loguru
class InterceptHandler(logging.Handler):
    """
    Default handler from Loguru documentation to intercept all standard logging
    and route it to Loguru.
    """
    def emit(self, record):
        # Get corresponding Loguru level if it exists
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller from where originated the logged message
        frame = logging.currentframe()
        depth = 2
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())

# Remove all existing handlers (including Loguru's default)
logger.remove()
logging.root.handlers = [InterceptHandler()]
logging.root.setLevel(logging.INFO)

# Redirect uvicorn and other libraries to use our InterceptHandler
for name in ["uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"]:
    _logger = logging.getLogger(name)
    _logger.handlers = [InterceptHandler()]
    _logger.propagate = False

# Add a high-performance async handler to stdout
logger.add(
    sys.stdout, 
    colorize=True, 
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    enqueue=True,  # This makes logging asynchronous (thread-safe, non-blocking)
    level="INFO"
)

def get_logger(name: str):
    """
    Returns an asynchronous Loguru logger bound to the specific module name.
    """
    return logger.bind(module=name)
