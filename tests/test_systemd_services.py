from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "system" / "deploy"
INSTALL_SCRIPT = ROOT / "system" / "scripts" / "install_systemd.sh"


CRITICAL_UNITS = {
    "neron-core.service": "core.app:app",
    "neron-llm.service": "-m llm.api.app",
    "neron-doctor.service": "doctor.app:app",
    "neron-web.service": "npm run dev",
    "neron-watchdog.service": "watchdog.app:app",
}


def test_critical_systemd_units_exist_and_target_live_modules():
    for unit, expected_exec_fragment in CRITICAL_UNITS.items():
        content = (DEPLOY_DIR / unit).read_text(encoding="utf-8")

        assert "[Service]" in content
        assert "WorkingDirectory=/etc/neron" in content
        assert expected_exec_fragment in content


def test_install_systemd_references_existing_deploy_units():
    script = INSTALL_SCRIPT.read_text(encoding="utf-8")
    unit_names = set(re.findall(r'"(neron-[^"]+\.service)"', script))

    assert CRITICAL_UNITS.keys() <= unit_names
    assert unit_names
    for unit in unit_names:
        assert (DEPLOY_DIR / unit).exists(), f"missing deploy unit referenced by installer: {unit}"


def test_legacy_neron_service_is_marked_and_not_used_by_server_script():
    legacy_unit = ROOT / "system" / "deploy" / "systemd" / "neron.service"
    server_script = ROOT / "system" / "scripts" / "server.sh"

    legacy_content = legacy_unit.read_text(encoding="utf-8")
    server_content = server_script.read_text(encoding="utf-8")

    assert "LEGACY" in legacy_content
    assert "server.core.app:app" in legacy_content
    assert 'SERVICE="neron-core.service"' in server_content
    assert 'SERVICE="neron.service"' not in server_content


def test_neronos_unit_uses_python_module_entrypoint_and_server_pythonpath():
    unit = ROOT / "system" / "deploy" / "systemd" / "neronOS.service"
    content = unit.read_text(encoding="utf-8")

    assert "WorkingDirectory=/etc/neronOS/server" in content
    assert "Environment=PYTHONPATH=/etc/neronOS/server" in content
    assert (
        "ExecStart=/etc/neronOS/venv/bin/python -m uvicorn core.app:app "
        "--host 0.0.0.0 --port 8010"
    ) in content


def test_goal_and_memory_units_use_current_runtime_paths():
    for name, module, port in (
        ("neron-goal.service", "goal.app:app", "8030"),
        ("neron-memory.service", "memory.app:app", "8040"),
    ):
        content = (ROOT / "system" / "deploy" / name).read_text(encoding="utf-8")

        assert "WorkingDirectory=/etc/neronOS/server" in content
        assert "Environment=NERON_ROOT=/etc/neronOS" in content
        assert "Environment=NERON_CONFIG=/etc/neronOS/neron.yaml" in content
        assert "/etc/neron/" not in content
        assert (
            f"/etc/neronOS/venv/bin/python -m uvicorn {module} "
            f"--host 127.0.0.1 --port {port}"
        ) in content
