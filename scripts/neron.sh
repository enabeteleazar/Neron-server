#!/usr/bin/env bash
# scripts/neron.sh

set -e
clear

# =========================
# COLORS
# =========================
BOLD="\033[1m"
BLUE="\033[34m"
YELLOW="\033[33m"
GREEN="\033[32m"
RED="\033[31m"
NC="\033[0m"

# =========================
# UI FUNCTIONS
# =========================
slow_echo() {
    local text="$1"
    local delay="${2:-0.02}"
    for ((i=0; i<${#text}; i++)); do
        printf "%s" "${text:$i:1}"
        sleep $delay
    done
    echo
}

spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\\'
    while ps -p "$pid" > /dev/null 2>&1; do
        local temp=${spinstr#?}
        printf " [%c]  " "${spinstr}"
        spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "      \b\b\b\b\b\b"
}

echo ""
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "  🤖 Configuration Néron"
echo -e "${BOLD}${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# =========================
# CONFIG
# =========================
BASE_DIR="/etc/neron"
SERVER_DIR="$BASE_DIR/server"
FILE="$SERVER_DIR/neron.yaml"

# =========================
# GUARD
# =========================
if [ ! -f "$FILE" ]; then
    echo -e "${RED}❌ neron.yaml introuvable${NC}"
    exit 1
fi

# =========================
# DISPLAY CONFIG
# =========================
python3 - <<EOF
import yaml

file = "$FILE"

with open(file) as f:
    data = yaml.safe_load(f)

def section(title):
    print("\n" + title)
    print("-" * len(title))

section("🤖 CORE NÉRON")
core = data.get("neron", {})
print(f"Version      : {core.get('version')}")
print(f"Log level    : {core.get('log_level')}")

section("🧠 LLM")
llm = data.get("llm", {})
print(f"Host         : {llm.get('host')}")
print(f"Model        : {llm.get('model')}")
print(f"Max tokens   : {llm.get('max_tokens')}")
print(f"Température  : {llm.get('temperature')}")

section("🧩 CODE AGENT")
ca = data.get("code_agent", {})
print(f"Enabled      : {ca.get('enabled')}")
print(f"Model        : {ca.get('model')}")
print(f"Timeout      : {ca.get('sandbox_timeout')}s")

section("💾 MEMORY")
mem = data.get("memory", {})
print(f"DB Path      : {mem.get('db_path')}")
print(f"Retention    : {mem.get('retention_days')} days")

section("📅 SCHEDULER")
sch = data.get("scheduler", {})
print(f"Enabled      : {sch.get('enabled')}")
print(f"Report hour  : {sch.get('daily_report_hour')}")
print(f"Cleanup days : {sch.get('memory_cleanup_days')}")

section("🌐 SYSTEM")
srv = data.get("server", {})
sys = data.get("system", {})
print(f"Host         : {srv.get('host')}")
print(f"Port         : {srv.get('port')}")
print(f"Watchdog     : {sys.get('watchdog_url')}")

section("🔌 INTEGRATIONS")

ha = data.get("home_assistant", {})
print("\nHome Assistant")
print(f"  Enabled : {ha.get('enabled')}")
print(f"  URL     : {ha.get('url')}")

tg = data.get("telegram", {})
print("\nTelegram")
print(f"  Enabled : {tg.get('enabled')}")
print(f"  Chat ID : {tg.get('chat_id')}")

tw = data.get("twilio", {})
print("\nTwilio")
print(f"  Enabled : {tw.get('enabled')}")

ws = data.get("watchdog", {})
print("\nWatchdog")
print(f"  Enabled    : {ws.get('enabled')}")
print(f"  CPU alert  : {ws.get('cpu_alert')}%")
print(f"  RAM alert  : {ws.get('ram_alert')}%")
print(f"  Disk alert : {ws.get('disk_alert')}%")

section("🔎 SEARCH")
sea = data.get("searxng", {})
print(f"URL          : {sea.get('url')}")
print(f"Timeout      : {sea.get('timeout')}s")
print(f"Max results  : {sea.get('max_results')}")
EOF

echo ""
echo -e "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
