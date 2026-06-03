# ============================================
# NÉRON AI — MAKEFILE (WRAPPER NERONCTL)
# ============================================

.PHONY: help install update backup restore telegram ollama client-install client-start neron

help:
	@neron

install:
	@neron install

update:
	@neron update

backup:
	@neron backup

restore:
	@neron restore

neron:
	@neron config

telegram:
	@neron telegram

ollama:
	@neron ollama

client-install:
	@neron client-install

client-start:
	@neron client-start
