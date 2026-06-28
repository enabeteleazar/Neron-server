#!/usr/bin/env bash

# Tuer l'ancienne session tmux
tmux kill-session -t n-server 2>/dev/null
tmux kill-session -t n-llm 2>/dev/null
# Vérifier qu'aucun uvicorn ne traîne
pkill -f "uvicorn core.app" || true
pkill -f "uvicorn neron_llm" || true
