"""Console logging utilities for tracing the assessment flow.

Every service in the auto-assessment pipeline logs to the console so the
progress of a run can be followed step by step.  Set the ``LOG_LEVEL``
environment variable (``DEBUG``/``INFO``/``WARNING``/``ERROR``) to control
verbosity, e.g. ``LOG_LEVEL=DEBUG python run.py``.
"""
import inspect
import logging
import os
import sys
import time
from contextlib import contextmanager
from functools import wraps
from typing import Optional

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)-26s | %(message)s"
DATE_FORMAT = "%H:%M:%S"

_configured = False


def configure_logging(level: Optional[str] = None) -> None:
    """Attach a console handler to the shared ``assessment`` logger."""
    global _configured
    if _configured:
        return

    resolved = (level or os.getenv("LOG_LEVEL") or "INFO").upper()
    numeric_level = getattr(logging, resolved, None)
    if not isinstance(numeric_level, int):
        numeric_level = logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))

    root = logging.getLogger("assessment")
    root.setLevel(numeric_level)
    root.handlers = [handler]
    root.propagate = False
    _configured = True


def get_logger(name: str) -> logging.Logger:
    """Return a console logger scoped under the ``assessment`` namespace."""
    configure_logging()
    return logging.getLogger(f"assessment.{name}")


@contextmanager
def step(logger: logging.Logger, description: str, **details):
    """Log the start, completion and failure of a flow step with timing."""
    suffix = " | " + " ".join(f"{k}={v}" for k, v in details.items()) if details else ""
    logger.info("-> %s%s", description, suffix)
    started = time.perf_counter()
    try:
        yield
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        logger.error("!! %s FAILED after %.0fms: %s", description, elapsed, exc)
        raise
    elapsed = (time.perf_counter() - started) * 1000
    logger.info("<- %s completed in %.0fms", description, elapsed)


def traced(func=None, *, name: Optional[str] = None):
    """Decorator logging entry, exit and duration of the wrapped function.

    Works with both sync and async functions.
    """
    def decorator(inner):
        label = name or inner.__qualname__
        log = get_logger(inner.__module__.rsplit(".", 1)[-1])

        if inspect.iscoroutinefunction(inner):
            @wraps(inner)
            async def async_wrapper(*args, **kwargs):
                log.info("-> %s(...)", label)
                started = time.perf_counter()
                try:
                    result = await inner(*args, **kwargs)
                except Exception as exc:
                    elapsed = (time.perf_counter() - started) * 1000
                    log.error("!! %s FAILED after %.0fms: %s", label, elapsed, exc)
                    raise
                elapsed = (time.perf_counter() - started) * 1000
                log.info("<- %s completed in %.0fms", label, elapsed)
                return result
            return async_wrapper

        @wraps(inner)
        def sync_wrapper(*args, **kwargs):
            log.info("-> %s(...)", label)
            started = time.perf_counter()
            try:
                result = inner(*args, **kwargs)
            except Exception as exc:
                elapsed = (time.perf_counter() - started) * 1000
                log.error("!! %s FAILED after %.0fms: %s", label, elapsed, exc)
                raise
            elapsed = (time.perf_counter() - started) * 1000
            log.info("<- %s completed in %.0fms", label, elapsed)
            return result
        return sync_wrapper

    if func is not None:
        return decorator(func)
    return decorator
