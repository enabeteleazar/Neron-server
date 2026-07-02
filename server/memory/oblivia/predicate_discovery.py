"""Deterministic predicate discovery for clear personal possession facts."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from .ontology import PREDICATES, PredicateDefinition
from .schemas import KnowledgeFact


@dataclass(frozen=True)
class PredicateCandidate:
    predicate: str
    cardinality: str
    lifecycle: str
    temporal: bool
    category: str
    labels: dict[str, str]
    confidence: float


@dataclass(frozen=True)
class DiscoveryDecision:
    predicate: str | None
    definition: PredicateDefinition | PredicateCandidate | None
    status: str
    requires_confirmation: bool = False


class PredicateDiscovery:
    """Map clear concepts and retain safe ontology candidates for review."""

    _nearby = {
        "telephone": "owns_device",
        "smartphone": "owns_device",
        "ordinateur": "owns_device",
        "appareil": "owns_device",
        "voiture": "owns_vehicle",
        "vehicule": "owns_vehicle",
        "objet": "owns_object",
        "achat": "purchased",
        "utilise": "uses_device",
    }

    def __init__(self) -> None:
        self.candidates: dict[str, PredicateCandidate] = {}

    def discover(self, concept: str) -> DiscoveryDecision:
        normalized = _normalize(concept)
        if normalized in PREDICATES:
            return DiscoveryDecision(
                normalized,
                PREDICATES[normalized],
                "known",
            )
        if normalized in self._nearby:
            predicate = self._nearby[normalized]
            return DiscoveryDecision(
                predicate,
                PREDICATES[predicate],
                "mapped",
            )
        candidate_name = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
        if not candidate_name or len(candidate_name) < 3:
            return DiscoveryDecision(
                None,
                None,
                "ambiguous",
                requires_confirmation=True,
            )
        candidate = PredicateCandidate(
            predicate=candidate_name,
            cardinality="many",
            lifecycle="accumulate",
            temporal=True,
            category="possessions",
            labels={"fr": concept.strip()},
            confidence=0.7,
        )
        self.candidates.setdefault(candidate_name, candidate)
        return DiscoveryDecision(candidate_name, candidate, "candidate")

    def extract(
        self,
        text: str,
        *,
        source: str,
    ) -> list[KnowledgeFact]:
        value = text.strip()
        patterns = (
            (
                "purchase",
                re.compile(
                    r"^j['’]ai achet[ée]\s+(?P<object>.+?)[.!?]*$",
                    re.IGNORECASE,
                ),
            ),
            (
                "owns",
                re.compile(
                    r"^j['’]ai\s+(?P<object>.+?)[.!?]*$",
                    re.IGNORECASE,
                ),
            ),
            (
                "owns",
                re.compile(
                    r"^je poss[èe]de\s+(?P<object>.+?)[.!?]*$",
                    re.IGNORECASE,
                ),
            ),
            (
                "uses",
                re.compile(
                    r"^j['’]utilise\s+(?P<object>.+?)[.!?]*$",
                    re.IGNORECASE,
                ),
            ),
            (
                "phone",
                re.compile(
                    r"^mon t[ée]l[ée]phone est\s+(?P<object>.+?)[.!?]*$",
                    re.IGNORECASE,
                ),
            ),
            (
                "computer",
                re.compile(
                    r"^mon ordinateur est\s+(?P<object>.+?)[.!?]*$",
                    re.IGNORECASE,
                ),
            ),
        )
        for operation, pattern in patterns:
            match = pattern.match(value)
            if not match:
                continue
            raw_object = re.split(
                r",\s*(?:il|elle|c['’]est)\b",
                match.group("object"),
                maxsplit=1,
                flags=re.IGNORECASE,
            )[0]
            object_name = _clean_object(raw_object)
            if not object_name:
                return []
            return self._facts(
                object_name,
                operation=operation,
                source=source,
                raw_text=value,
            )
        return []

    def _facts(
        self,
        object_name: str,
        *,
        operation: str,
        source: str,
        raw_text: str,
    ) -> list[KnowledgeFact]:
        device = _classify_device(object_name)
        if operation in {"phone", "computer", "uses"} or device:
            predicate = "uses_device" if operation == "uses" else "owns_device"
            device_slot = (
                operation
                if operation in {"phone", "computer"}
                else (device or {}).get("slot", "device")
            )
            metadata = {
                "device_slot": device_slot,
                "discovered_by": "predicate_discovery",
            }
        elif _contains(object_name, ("voiture", "vehicule", "véhicule")):
            predicate = "owns_vehicle"
            metadata = {"discovered_by": "predicate_discovery"}
        else:
            predicate = "owns_object"
            metadata = {"discovered_by": "predicate_discovery"}

        facts = [
            KnowledgeFact(
                subject="user",
                predicate=predicate,
                object=object_name,
                source=source,
                raw_text=raw_text,
                metadata=metadata,
            )
        ]
        if operation == "purchase":
            facts.append(
                KnowledgeFact(
                    subject="user",
                    predicate="purchased",
                    object=object_name,
                    source=source,
                    raw_text=raw_text,
                    metadata={"acquisition": "purchase"},
                )
            )
            facts.append(
                KnowledgeFact(
                    subject=object_name,
                    predicate="acquired_by",
                    object="purchase",
                    source=source,
                    raw_text=raw_text,
                )
            )
        if device:
            facts.append(
                KnowledgeFact(
                    subject=object_name,
                    predicate="type",
                    object=device["type"],
                    source=source,
                    raw_text=raw_text,
                )
            )
            if device.get("brand"):
                facts.append(
                    KnowledgeFact(
                        subject=object_name,
                        predicate="brand",
                        object=device["brand"],
                        source=source,
                        raw_text=raw_text,
                    )
                )
        return facts


def _normalize(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(
        char for char in value if not unicodedata.combining(char)
    )
    return " ".join(
        re.sub(r"[^a-z0-9 ]+", " ", value).split()
    )


def _clean_object(value: str) -> str:
    cleaned = value.strip().rstrip(".!?")
    cleaned = re.sub(
        r"^(?:l['’]|le |la |les |un |une )",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )
    return cleaned.strip()


def _contains(value: str, tokens: tuple[str, ...]) -> bool:
    normalized = value.casefold()
    return any(token in normalized for token in tokens)


def _classify_device(value: str) -> dict[str, str] | None:
    normalized = value.casefold()
    if any(token in normalized for token in ("iphone", "smartphone", "téléphone")):
        return {
            "slot": "phone",
            "type": "smartphone",
            **({"brand": "Apple"} if "iphone" in normalized else {}),
        }
    if any(token in normalized for token in ("ordinateur", "macbook", "laptop", " pc")):
        return {
            "slot": "computer",
            "type": "computer",
            **({"brand": "Apple"} if "macbook" in normalized else {}),
        }
    if any(token in normalized for token in ("ipad", "tablette")):
        return {
            "slot": "tablet",
            "type": "tablet",
            **({"brand": "Apple"} if "ipad" in normalized else {}),
        }
    return None
