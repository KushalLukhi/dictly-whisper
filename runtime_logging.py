"""
runtime_logging.py - File logging for console and packaged EXE runs.
"""

from __future__ import annotations

import io
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
import sys
import threading
import traceback

import config_manager

LOG_DIR = config_manager.APP_DIR / "logs"
LOG_FILE = LOG_DIR / "dictly.log"


class _TeeLogger(io.TextIOBase):
    def __init__(self, logger: logging.Logger, level: int, stream):
        self._logger = logger
        self._level = level
        self._stream = stream
        self._buffer = ""

    def write(self, data):
        if not data:
            return 0

        if self._stream is not None:
            self._stream.write(data)
            self._stream.flush()

        self._buffer += data
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            line = line.rstrip()
            if line:
                self._logger.log(self._level, line)
        return len(data)

    def flush(self):
        if self._stream is not None:
            self._stream.flush()
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.rstrip())
        self._buffer = ""


def get_log_file() -> Path:
    config_manager.ensure_app_dir()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_FILE


def _log_uncaught_exception(exc_type, exc_value, exc_tb):
    logging.getLogger("dictly").error(
        "Uncaught exception\n%s",
        "".join(traceback.format_exception(exc_type, exc_value, exc_tb)).rstrip(),
    )


def _log_thread_exception(args):
    logging.getLogger("dictly").error(
        "Unhandled thread exception in %s\n%s",
        args.thread.name if args.thread else "unknown-thread",
        "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)).rstrip(),
    )


def configure_logging() -> Path:
    log_file = get_log_file()
    root = logging.getLogger()
    if root.handlers:
        return log_file

    root.setLevel(logging.INFO)
    handler = RotatingFileHandler(log_file, maxBytes=512 * 1024, backupCount=3, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    root.addHandler(handler)

    sys.stdout = _TeeLogger(logging.getLogger("stdout"), logging.INFO, getattr(sys, "__stdout__", None))
    sys.stderr = _TeeLogger(logging.getLogger("stderr"), logging.ERROR, getattr(sys, "__stderr__", None))
    sys.excepthook = _log_uncaught_exception
    threading.excepthook = _log_thread_exception
    logging.getLogger("dictly").info("Logging to %s", log_file)
    return log_file
