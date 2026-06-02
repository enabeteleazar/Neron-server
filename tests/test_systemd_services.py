from __future__ import annotations

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEPLOY_DIR = ROOT / "deploy"
INSTALL_SCRIPT = ROOT / "scripts" / "install_systemd.sh"


CRITICAL_UNITS = {
    "neron-core.service": "core.app:app",
    "neron-self-model-loop.service": "-m core.self_model.self_model_loop",
    "neron-world-model-loop.service": "-m core.world_model.world_model_loop",
    "neron-cognitive-loop.service": "core/autonomous/run_cognitive_loop.py",
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
