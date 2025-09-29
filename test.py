from loguru import logger

try:
    import RPi.GPIO as GPIO
    IS_PI = True
except (RuntimeError, ModuleNotFoundError):
    IS_PI = False
    logger.warning("RPi.GPIO library not found. GPIO functionality will be disabled.")
