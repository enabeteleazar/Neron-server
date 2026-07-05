from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "server"
LEGACY_ROOT = "/etc/neron"


def test_runtime_python_has_no_legacy_etc_neron_default():
    offenders = []
    for path in SERVER.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        if path.relative_to(SERVER).as_posix() == "doctor/test_unit.py":
            continue
        if LEGACY_ROOT in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(path.relative_to(ROOT).as_posix())

    assert offenders == []


def test_canonical_paths_default_to_current_runtime(monkeypatch):
    monkeypatch.delenv("NERON_ROOT", raising=False)
    monkeypatch.delenv("NERON_CONFIG", raising=False)

    source = (SERVER / "common" / "paths.py").read_text(encoding="utf-8")

    assert 'os.getenv("NERON_ROOT", "/etc/neronOS")' in source
    assert 'os.getenv("NERON_CONFIG", str(NERON_ROOT / "neron.yaml"))' in source
