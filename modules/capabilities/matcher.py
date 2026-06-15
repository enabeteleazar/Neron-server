from __future__ import annotations

import json
from collections.abc import Iterable

from modules.capabilities.domain_classifier import DomainClassifier
from modules.capabilities.intent_extractor import IntentExtractor
from modules.capabilities.models import (
    Capability,
    CapabilityMatch,
    IntentUnderstanding,
)
from modules.capabilities.router import normalize_text
from tools.registry import ToolRegistry, get_tool_registry


_STOPWORDS = {
    "agent",
    "analyse",
    "analyser",
    "neron",
    "outil",
    "pour",
    "tool",
    "une",
    "des",
    "les",
    "qui",
}


class CapabilityMatcher:
    def __init__(
        self,
        *,
        domain_classifier: DomainClassifier | None = None,
        intent_extractor: IntentExtractor | None = None,
        tool_registry: ToolRegistry | None = None,
        minimum_score: float = 0.58,
    ) -> None:
        self.domain_classifier = domain_classifier or DomainClassifier()
        self.intent_extractor = intent_extractor or IntentExtractor()
        self.tool_registry = tool_registry or get_tool_registry()
        self.minimum_score = minimum_score

    def match(
        self,
        text: str,
        understanding: IntentUnderstanding,
        capabilities: Iterable[Capability],
        *,
        capability_type: str | None = None,
    ) -> CapabilityMatch | None:
        matches = self.score_capabilities(
            text,
            understanding,
            capabilities,
            capability_type=capability_type,
        )
        if not matches or matches[0].score < self.minimum_score:
            return None
        return matches[0]

    def score_capabilities(
        self,
        text: str,
        understanding: IntentUnderstanding,
        capabilities: Iterable[Capability],
        *,
        capability_type: str | None = None,
    ) -> list[CapabilityMatch]:
        query_tokens = self._tokens(text)
        matches: list[CapabilityMatch] = []
        for capability in capabilities:
            if capability_type and capability.capability_type != capability_type:
                continue
            searchable = self._searchable(capability)
            capability_domain = self.domain_classifier.classify(searchable)
            capability_intent = self.intent_extractor.extract(searchable)
            lexical_score = self._lexical_score(query_tokens, self._tokens(searchable))
            domain_score = self._domain_score(
                understanding.domain.domain,
                capability_domain.domain,
            )
            intent_score = self._intent_score(
                understanding.intent.action,
                capability_intent.action,
            )
            score = round(
                domain_score * 0.62
                + intent_score * 0.18
                + lexical_score * 0.20,
                3,
            )
            if (
                understanding.domain.domain != "unknown"
                and capability_domain.domain != "unknown"
                and understanding.domain.domain != capability_domain.domain
            ):
                score = min(score, 0.18)
            matches.append(
                CapabilityMatch(
                    capability=capability,
                    score=score,
                    domain_score=domain_score,
                    intent_score=intent_score,
                    lexical_score=lexical_score,
                    missing_tools=self._missing_tools(capability),
                )
            )
        return sorted(matches, key=lambda match: match.score, reverse=True)

    def _searchable(self, capability: Capability) -> str:
        return " ".join(
            [
                capability.slug,
                capability.name,
                capability.description,
                *capability.aliases,
                json.dumps(capability.metadata, ensure_ascii=False, sort_keys=True),
            ]
        )

    def _tokens(self, text: str) -> set[str]:
        return {
            token
            for token in normalize_text(text).split()
            if len(token) >= 3 and token not in _STOPWORDS
        }

    def _lexical_score(self, query: set[str], candidate: set[str]) -> float:
        if not query:
            return 0.0
        return round(len(query & candidate) / len(query), 3)

    def _domain_score(self, requested: str, candidate: str) -> float:
        if requested == candidate and requested != "unknown":
            return 1.0
        if requested == "unknown" and candidate == "unknown":
            return 0.35
        if requested == "unknown" or candidate == "unknown":
            return 0.2
        return 0.0

    def _intent_score(self, requested: str, candidate: str) -> float:
        if requested == candidate:
            return 1.0
        compatible = {
            ("analyse", "resume"),
            ("resume", "analyse"),
            ("diagnostic", "analyse"),
            ("analyse", "diagnostic"),
            ("surveillance", "notification"),
            ("notification", "surveillance"),
        }
        return 0.65 if (requested, candidate) in compatible else 0.15

    def _missing_tools(self, capability: Capability) -> list[str]:
        spec = capability.metadata.get("spec")
        if not isinstance(spec, dict):
            return []
        declared = spec.get("tools") or spec.get("required_tools") or []
        if not isinstance(declared, list):
            return []
        return [
            str(slug)
            for slug in declared
            if not self.tool_registry.tool_exists(str(slug))
        ]
