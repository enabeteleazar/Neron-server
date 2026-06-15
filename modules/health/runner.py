# doctor/runner.py
# Orchestrateur principal — coordonne analyse, tests, fixes, monitoring

from doctor.analyzer import analyze_project
from doctor.tester import test_services
from doctor.fixer import apply_fixes
from doctor.monitor import get_system_metrics, get_all_services_status, get_all_journal_errors
from doctor.config import cfg


def run_full_diagnosis() -> dict:
    report = {
        "analysis": {},
        "monitor": {},
        "tests": {},
        "fixes": [],
        "final_status": {}
    }

    # PHASE 1 - ANALYSE STATIQUE
    report["analysis"]["core"] = analyze_project(cfg.CORE_PATH)
    report["analysis"]["llm"]  = analyze_project(cfg.LLM_PATH)

    # PHASE 2 - MONITORING SYSTÈME
    report["monitor"]["system"]   = get_system_metrics()
    report["monitor"]["services"] = get_all_services_status()
    report["monitor"]["journals"] = get_all_journal_errors()

    # PHASE 3 - TESTS RUNTIME
    report["tests"] = test_services()

    # PHASE 4 - AUTOCORRECTION
    report["fixes"] = apply_fixes(report)

    # PHASE 5 - RE-TEST POST FIX
    report["final_status"] = test_services()

    return report
