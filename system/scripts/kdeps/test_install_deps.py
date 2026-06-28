from pathlib import Path
import importlib.util
import subprocess


def _load_module(module_name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(module_name, Path(relative_path))
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


install_deps = _load_module("install_deps", "scripts/install_deps.py")


def test_install_packages_skips_installed_package(monkeypatch):
    calls = []
    monkeypatch.setattr(install_deps.importlib.util, "find_spec", lambda name: object())
    monkeypatch.setattr(subprocess, "check_call", lambda cmd: calls.append(cmd))

    install_deps.install_packages(["requests"])

    assert calls == []


def test_install_packages_installs_missing_package(monkeypatch, capsys):
    calls = []
    monkeypatch.setattr(install_deps.importlib.util, "find_spec", lambda name: None)
    monkeypatch.setattr(subprocess, "check_call", lambda cmd: calls.append(cmd))

    install_deps.install_packages(["missing_pkg"])

    assert calls == [[install_deps.sys.executable, "-m", "pip", "install", "missing_pkg"]]
    assert "Module missing_pkg manquant, installation..." in capsys.readouterr().out
