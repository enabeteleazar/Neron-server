from __future__ import annotations

AGENT_SPEC = {
    "capabilities": [
        "deterministic_response"
    ],
    "goal": "Créer un agent durable qui répond à cette demande : Analyse automatiquement les logs Néron et résume les erreurs critiques",
    "inputs": [
        "text"
    ],
    "kind": "agent",
    "name": "durable_repond_a_agent",
    "outputs": [
        "response"
    ],
    "safety": {
        "filesystem": "limited",
        "network": "none_required"
    },
    "title": "Agent durable_repond_a_agent",
    "tools": [
        "neron_log_reader_tool",
        "neron_log_error_filter_tool",
        "neron_log_summary_tool"
    ]
}
AGENT_SPEC_SIGNATURE = 'capabilities deterministic response goal creer un agent durable qui repond a cette demande analyse automatiquement les logs neron et resume les erreurs critiques inputs text kind agent name durable repond a agent outputs response safety filesystem limited network none required title agent durable repond a agent tools neron log reader tool neron log error filter tool neron log summary tool'

import re


ERROR_PATTERN = re.compile(
    r"\b(ERROR|CRITICAL|FATAL|Traceback|Exception)\b",
    re.IGNORECASE,
)


class Agent:
    name = 'durable_repond_a_agent'

    async def execute(self, text: str = "", tools=None, context=None) -> dict:
        if tools:
            payload = dict(getattr(context, "context", {}) or {})
            reader = await tools["neron_log_reader_tool"].execute(payload)
            if not reader.ok:
                raise RuntimeError(reader.error or "log_reader_failed")
            filtered = await tools["neron_log_error_filter_tool"].execute(
                {"logs": reader.data.get("logs", [])}
            )
            if not filtered.ok:
                raise RuntimeError(filtered.error or "log_filter_failed")
            summary = await tools["neron_log_summary_tool"].execute(
                {"errors": filtered.data.get("errors", [])}
            )
            if not summary.ok:
                raise RuntimeError(summary.error or "log_summary_failed")
            return {
                "status": "ok",
                "agent": self.name,
                "response": summary.response,
                **summary.data,
            }

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        errors = [line for line in lines if ERROR_PATTERN.search(line)]
        if not errors:
            response = "Analyse des logs Néron : aucune erreur critique détectée."
        else:
            severity = "CRITICAL" if any(
                token in line.upper()
                for line in errors
                for token in ("CRITICAL", "FATAL")
            ) else "ERROR"
            excerpt = errors[0][:180]
            response = (
                f"Analyse des logs Néron : {len(errors)} erreur(s), "
                f"gravité {severity}. Extrait : {excerpt}. "
                "Recommandation : vérifier le composant concerné."
            )
        return {
            "status": "ok",
            "agent": self.name,
            "response": response,
            "error_count": len(errors),
        }
