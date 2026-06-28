from __future__ import annotations

from abc import ABC, abstractmethod

from modules.capabilities.domain_classifier import DomainClassifier
from modules.capabilities.intent_extractor import IntentExtractor
from modules.capabilities.models import IntentUnderstanding


class IntentProvider(ABC):
    @abstractmethod
    async def classify(self, text: str) -> IntentUnderstanding:
        raise NotImplementedError


class RuleBasedIntentProvider(IntentProvider):
    def __init__(
        self,
        *,
        domain_classifier: DomainClassifier | None = None,
        intent_extractor: IntentExtractor | None = None,
    ) -> None:
        self.domain_classifier = domain_classifier or DomainClassifier()
        self.intent_extractor = intent_extractor or IntentExtractor()

    def classify_sync(self, text: str) -> IntentUnderstanding:
        return IntentUnderstanding(
            domain=self.domain_classifier.classify(text),
            intent=self.intent_extractor.extract(text),
            provider="rules",
        )

    async def classify(self, text: str) -> IntentUnderstanding:
        return self.classify_sync(text)


class LlmIntentProvider(IntentProvider):
    async def classify(self, text: str) -> IntentUnderstanding:
        raise NotImplementedError("LlmIntentProvider is reserved for a future version")
