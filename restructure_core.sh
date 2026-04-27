#!/bin/bash

set -e

CORE="/etc/neron/core"

echo "[1/8] Creating new architecture..."

mkdir -p $CORE/gateway
mkdir -p $CORE/control_plane
mkdir -p $CORE/pipeline/intent
mkdir -p $CORE/pipeline/routing
mkdir -p $CORE/pipeline/policy
mkdir -p $CORE/pipeline/execution
mkdir -p $CORE/memory/world_model
mkdir -p $CORE/events
mkdir -p $CORE/observability

echo "[2/8] Moving gateway..."

mv $CORE/modules/gateway.py $CORE/gateway/ 2>/dev/null || true

echo "[3/8] Moving intent (orchestrator)..."

mv $CORE/orchestrator/intent_router.py $CORE/pipeline/intent/ 2>/dev/null || true

echo "[4/8] Moving routing..."

mv $CORE/modules/agent_router.py $CORE/pipeline/routing/ 2>/dev/null || true

echo "[5/8] Moving world model..."

mv $CORE/modules/world_model.py $CORE/memory/world_model/ 2>/dev/null || true
mv $CORE/world_model/* $CORE/memory/world_model/ 2>/dev/null || true

echo "[6/8] Moving agents..."

mv $CORE/agents $CORE/agents_backup_old 2>/dev/null || true
mkdir -p $CORE/agents

echo "[7/8] Moving llm client (keep as-is but isolate)..."

mv $CORE/llm_client $CORE/llm 2>/dev/null || true

echo "[8/8] Cleaning old modules..."

rm -rf $CORE/modules
rm -rf $CORE/orchestrator

echo "DONE: Core restructured to new architecture"
