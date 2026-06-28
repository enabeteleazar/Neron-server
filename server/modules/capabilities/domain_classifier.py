from __future__ import annotations

from modules.capabilities.models import DomainClassification
from modules.capabilities.rules import RuleEngine


class DomainClassifier:
    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self.rule_engine = rule_engine or RuleEngine()

    def classify(self, text: str) -> DomainClassification:
        match = self.rule_engine.best_match(text)
        if match is None:
            return DomainClassification(
                domain="unknown",
                confidence=0.0,
                evidence=[],
            )
        return DomainClassification(
            domain=match.domain,
            confidence=match.confidence,
            evidence=match.matched_terms,
        )
