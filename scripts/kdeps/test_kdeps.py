from pathlib import Path
import importlib.util
import subprocess


def _load_module(module_name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(relative_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


kdeps = _load_module("kdeps", "scripts/kdeps.py")


def test_install_packages_runs_pip_for_each_package(monkeypatch):
    calls = []
    monkeypatch.setattr(subprocess, "run", lambda cmd: calls.append(cmd))

    kdeps.install_packages(["a", "b"])

    assert calls == [["pip", "install", "a"], ["pip", "install", "b"]]


def test_check_package_returns_true_when_importable(monkeypatch):
    monkeypatch.setattr(kdeps.importlib.util, "find_spec", lambda name: object())

    assert kdeps.check_package("json") is True


def test_check_package_returns_false_when_missing(monkeypatch):
    monkeypatch.setattr(kdeps.importlib.util, "find_spec", lambda name: None)

    assert kdeps.check_package("not_there") is False
