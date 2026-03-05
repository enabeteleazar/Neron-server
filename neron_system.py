#!/usr/bin/env python3
import multiprocessing
import subprocess
import sys
import os
import time
import signal
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "neron_system.log")
from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))

SERVICES = [
    {"name": "neron-memory",   "module": "modules.neron_memory.app:app",   "port": 8002, "critical": True,  "delay": 0},
    {"name": "neron-llm",      "module": "modules.neron_llm.app:app",      "port": 5000, "critical": True,  "delay": 2},
    {"name": "neron-core",     "module": "modules.neron_core.app:app",     "port": 8000, "critical": True,  "delay": 3},
    {"name": "neron-stt",      "module": "modules.neron_stt.app:app",      "port": 8001, "critical": False, "delay": 1},
    {"name": "neron-tts",      "module": "modules.neron_tts.app:app",      "port": 8003, "critical": False, "delay": 1},
    {"name": "neron-telegram", "module": "modules.neron_telegram.app:app", "port": 8010, "critical": False, "delay": 2},
    {"name": "neron-watchdog", "module": "modules.neron_watchdog.app:api", "port": 8004, "critical": False, "delay": 2},
]

MAX_RETRIES = 5
CRASH_WINDOW = 10
RESTART_DELAY = 2
stop_event = multiprocessing.Event()

def log(level, msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = "[%s] [%s] %s" % (ts, level, msg)
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def check_ollama():
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)
        if "llama3.2:3b" not in result.stdout:
            log("ERROR", "Modele llama3.2:3b manquant")
            sys.exit(1)
        log("INFO", "Ollama OK")
    except FileNotFoundError:
        log("ERROR", "Ollama non trouve")
        sys.exit(1)

def run_service(service):
    module_dir = os.path.join(BASE_DIR, "modules", service["name"].replace("neron-", "neron_"))
    if os.path.exists(module_dir):
        sys.path.insert(0, module_dir)
    sys.path.insert(0, BASE_DIR)
    import uvicorn
    uvicorn.run(service["module"], host="0.0.0.0", port=service["port"], log_level="info", reload=False)

def supervise(service):
    name = service["name"]
    retries = 0
    while not stop_event.is_set():
        t_start = time.time()
        proc = multiprocessing.Process(target=run_service, args=(service,), name=name, daemon=False)
        proc.start()
        log("INFO", "%s demarre (PID %d)" % (name, proc.pid))
        proc.join()
        if stop_event.is_set():
            break
        uptime = time.time() - t_start
        retries = retries + 1 if uptime < CRASH_WINDOW else 0
        log("WARN", "%s arrete (uptime=%.1fs, retries=%d/%d)" % (name, uptime, retries, MAX_RETRIES))
        if retries >= MAX_RETRIES:
            log("CRIT", "%s abandon" % name)
            if service.get("critical"):
                stop_event.set()
                os.kill(os.getpid(), signal.SIGTERM)
            return
        time.sleep(RESTART_DELAY)

def handle_signal(sig, frame):
    log("INFO", "Arret")
    stop_event.set()

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)
    print("\n  NERON SYSTEM - Monolithe v2.0\n")
    log("INFO", "=== Neron System demarrage ===")
    check_ollama()
    for svc in SERVICES:
        if svc.get("delay", 0) > 0:
            time.sleep(svc["delay"])
        t = threading.Thread(target=supervise, args=(svc,), daemon=True)
        t.start()
    log("INFO", "Tous les services demarres")
    try:
        while not stop_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        stop_event.set()
    log("INFO", "=== Neron System arret ===")
