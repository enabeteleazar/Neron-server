from __future__ import annotations

import importlib
import logging
import os
import sys


def _reload_logging_setup(monkeypatch):
    logger = logging.getLogger("neron")
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
    sys.modules.pop("core.logging.setup", None)
    monkeypatch.setattr(
        "logging.handlers.RotatingFileHandler",
        lambda *args, **kwargs: logging.NullHandler(),
    )
    return importlib.import_module("core.logging.setup")


def test_logging_uses_configured_logs_dir(tmp_path, monkeypatch):
    logs_dir = tmp_path / "logs"
    monkeypatch.setenv("NERON_LOGS_DIR", str(logs_dir))

    setup = _reload_logging_setup(monkeypatch)

    assert setup.LOGS_DIR == logs_dir
    assert logs_dir.exists()


def test_logging_falls_back_when_default_log_dir_is_not_writable(monkeypatch):
    monkeypatch.delenv("NERON_LOGS_DIR", raising=False)

    real_access = os.access

    def fake_access(path, mode):
        if str(path) == "/var/log/neron":
            return False
        return real_access(path, mode)

    monkeypatch.setattr(os, "access", fake_access)

    setup = _reload_logging_setup(monkeypatch)

    assert setup.LOGS_DIR == setup.FALLBACK_LOGS_DIR
