# app/runner.py
# Orchestrateur Principal

from app.analyzer import analyze_project
from app.tester import test_services
from app.fixer import apply_fixes

SERVER_PATH = "/etc/neron/server"
LLM_PATH = "/etc/neron/llm"


def run_full_diagnosis():
    report = {
        "analysis": {},
        "tests": {},
        "fixes": [],
        "final_status": {}
    }

    # PHASE 1 - ANALYSE
    report["analysis"]["server"] = analyze_project(SERVER_PATH)
    report["analysis"]["llm"] = analyze_project(LLM_PATH)

    # PHASE 2 - TEST RUN
    report["tests"] = test_services()

    # PHASE 3 - FIXES AUTO
    report["fixes"] = apply_fixes(report)

    # PHASE 4 - RE-TEST
    report["final_status"] = test_services()

    return report
