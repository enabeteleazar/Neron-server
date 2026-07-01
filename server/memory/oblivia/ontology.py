"""Declarative ontology for Oblivia knowledge lifecycles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Cardinality = Literal["one", "many"]
Lifecycle = Literal[
    "immutable",
    "replace",
    "accumulate",
    "preference",
    "event",
]


@dataclass(frozen=True)
class PredicateDefinition:
    predicate: str
    cardinality: Cardinality
    lifecycle: Lifecycle
    temporal: bool
    category: str
    labels: dict[str, str]
    inverse_predicate: str | None = None
    recall_templates: dict[str, str] = field(default_factory=dict)


PREDICATES: dict[str, PredicateDefinition] = {
    "birth_date": PredicateDefinition(
        "birth_date", "one", "immutable", True, "identity",
        {"fr": "date de naissance"},
    ),
    # Product decision: names are replaceable and retain visible history.
    "name": PredicateDefinition(
        "name", "one", "replace", True, "identity",
        {"fr": "prénom"},
    ),
    "lives_at": PredicateDefinition(
        "lives_at", "one", "replace", True, "location",
        {"fr": "lieu de résidence"},
    ),
    "works_at": PredicateDefinition(
        "works_at", "one", "replace", True, "professional",
        {"fr": "employeur"},
    ),
    # Product decision: spouse is replaceable (separation/remarriage).
    "spouse": PredicateDefinition(
        "spouse", "one", "replace", True, "relationship",
        {"fr": "conjoint"},
        inverse_predicate="spouse_of",
    ),
    "likes": PredicateDefinition(
        "likes", "many", "preference", True, "preference",
        {"fr": "préférence positive"},
    ),
    "dislikes": PredicateDefinition(
        "dislikes", "many", "preference", True, "preference",
        {"fr": "préférence négative"},
    ),
    "has_child": PredicateDefinition(
        "has_child", "many", "accumulate", True, "relationship",
        {"fr": "enfant"},
        inverse_predicate="relation_to_user",
    ),
    "has_pet": PredicateDefinition(
        "has_pet", "many", "accumulate", True, "relationship",
        {"fr": "animal"},
    ),
    "speaks_language": PredicateDefinition(
        "speaks_language", "many", "accumulate", True, "capability",
        {"fr": "langue parlée"},
    ),
    "owns_vehicle": PredicateDefinition(
        "owns_vehicle", "many", "accumulate", True, "ownership",
        {"fr": "véhicule possédé"},
    ),
    "projects": PredicateDefinition(
        "projects", "many", "accumulate", True, "project",
        {"fr": "projet"},
    ),
    "relation_to_user": PredicateDefinition(
        "relation_to_user", "many", "accumulate", True, "relationship",
        {"fr": "relation avec l’utilisateur"},
    ),
    "children_count": PredicateDefinition(
        "children_count", "one", "replace", True, "relationship",
        {"fr": "nombre d’enfants"},
    ),
    "is": PredicateDefinition(
        "is", "many", "accumulate", True, "identity",
        {"fr": "est"},
    ),
}

# The lifecycle is declared for future event predicates, but no event
# predicate is registered in this mission.
SUPPORTED_LIFECYCLES: tuple[Lifecycle, ...] = (
    "immutable",
    "replace",
    "accumulate",
    "preference",
    "event",
)


def get_predicate(predicate: str) -> PredicateDefinition:
    try:
        return PREDICATES[predicate]
    except KeyError as exc:
        raise ValueError(f"unknown ontology predicate: {predicate}") from exc

