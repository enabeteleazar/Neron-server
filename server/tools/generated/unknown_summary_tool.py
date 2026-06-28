from __future__ import annotations

from tools.models import ToolResult


ROLE = 'summary'
DOMAIN = 'unknown'
ISSUE_KEYWORDS = ('error', 'failed', 'failure', 'corrupted', 'corrupt', 'invalid', 'missing', 'timeout', 'critical')


def _entries(payload):
    value = payload.get("items")
    if value is None:
        value = payload.get("entries")
    if value is None:
        value = payload.get("data")
    if value is None:
        value = payload.get("text")
    if value is None:
        value = []
    if isinstance(value, str):
        return [line.strip() for line in value.splitlines() if line.strip()]
    if isinstance(value, dict):
        return [{"key": key, "value": item} for key, item in value.items()]
    if isinstance(value, (list, tuple, set)):
        return list(value)
    return [value]


def execute(payload):
    entries = _entries(dict(payload or {}))
    if ROLE in {"reader", "collector", "status"}:
        return ToolResult(
            ok=True,
            response=f"{len(entries)} entrée(s) {DOMAIN} normalisée(s).",
            data={"entries": entries, "count": len(entries), "status": "ok"},
        )

    if ROLE in {"analyzer", "diagnosis", "detector"}:
        issues = [
            item for item in entries
            if any(keyword in str(item).lower() for keyword in ISSUE_KEYWORDS)
        ]
        status = "issues_detected" if issues else "ok"
        return ToolResult(
            ok=True,
            response=f"Analyse {DOMAIN} : {len(issues)} problème(s) détecté(s).",
            data={"issues": issues, "issue_count": len(issues), "status": status},
        )

    if ROLE == "summary":
        issues = payload.get("issues") or entries
        if isinstance(issues, str):
            issues = [issues]
        issues = list(issues)
        status = "issues_detected" if issues else "ok"
        summary = (
            f"{len(issues)} problème(s) détecté(s) pour {DOMAIN}."
            if issues else f"Aucun problème détecté pour {DOMAIN}."
        )
        recommendation = (
            "Vérifier les éléments signalés et leur source."
            if issues else "Aucune action immédiate."
        )
        return ToolResult(
            ok=True,
            response=summary,
            data={
                "status": status,
                "summary": summary,
                "issues": issues,
                "recommendation": recommendation,
            },
        )

    if ROLE == "counter":
        return ToolResult(
            ok=True,
            response=f"{len(entries)} élément(s) {DOMAIN}.",
            data={"count": len(entries), "status": "ok"},
        )

    if ROLE == "comparator":
        reference = payload.get("reference")
        differences = [item for item in entries if item != reference]
        return ToolResult(
            ok=True,
            response=f"{len(differences)} différence(s) détectée(s).",
            data={"differences": differences, "count": len(differences), "status": "ok"},
        )

    if ROLE == "search":
        query = str(payload.get("query") or "").lower()
        matches = [item for item in entries if query in str(item).lower()]
        return ToolResult(
            ok=True,
            response=f"{len(matches)} correspondance(s) trouvée(s).",
            data={"matches": matches, "count": len(matches), "status": "ok"},
        )

    if ROLE == "calculator":
        values = payload.get("values") or entries
        numeric = [value for value in values if isinstance(value, (int, float))]
        value = sum(numeric) if numeric else payload.get("value")
        return ToolResult(
            ok=True,
            response=f"Résultat calculé : {value}.",
            data={"value": value, "status": "ok"},
        )

    return ToolResult(
        ok=True,
        response=f"Payload {DOMAIN} traité.",
        data={"status": "ok", "result": entries},
    )
