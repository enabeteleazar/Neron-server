"""Deterministic reasoning over Oblivia's structured user facts."""

from __future__ import annotations

import re
import unicodedata
from typing import TYPE_CHECKING

from .schemas import LifecycleKnowledgeFact
from .timeline import project_unique_timeline

if TYPE_CHECKING:
    from .sqlite_adapter import SQLiteMemoryAdapter


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKD", value.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.sub(r"[^a-z0-9 ]+", " ", text).split())


def _join_french(values: list[str]) -> str:
    if len(values) < 2:
        return values[0] if values else ""
    return ", ".join(values[:-1]) + f" et {values[-1]}"


def _timeline_key(fact: LifecycleKnowledgeFact) -> tuple[str, str]:
    return (fact.valid_from, fact.valid_to or "")


class MemoryReasoner:
    """Answer aggregate and semantic-alias questions without an LLM."""

    _profile_questions = {
        "qui suis je",
        "parle moi de moi",
        "presente moi",
        "que sais tu de moi",
        "fais un resume de ce que tu sais sur moi",
    }
    _spouse_questions = {"qui est ma femme", "qui est mon epouse"}
    _works_history_questions = {"ou ai je travaille"}
    _likes_current_questions = {
        "qu est ce que j aime",
        "j aime quoi",
    }
    _likes_history_questions = {"qu est ce que j aimais avant"}

    def __init__(self, store: SQLiteMemoryAdapter) -> None:
        self.store = store

    def answer(self, question: str) -> dict | None:
        query = _normalize(question)
        facts = self.store.list_facts(limit=1_000)

        if query in self._profile_questions:
            return self._result(self._profile(facts), self._active_user(facts))
        if query in self._spouse_questions:
            relevant = self._current(facts, "spouse")
            if not relevant:
                relevant = [
                    fact
                    for fact in facts
                    if fact.subject == "user.spouse"
                    and fact.predicate == "name"
                    and fact.is_current
                    and not fact.retracted
                    and not fact.conflict
                ]
            answer = (
                f"Ta femme s'appelle {relevant[-1].object}."
                if relevant
                else "Je ne connais pas le nom de ta femme."
            )
            return self._result(answer, relevant)
        if query in self._works_history_questions:
            relevant = self._timeline(facts, "works_at")
            answer = (
                "Tu as travaillé chez "
                + ", puis chez ".join(fact.object for fact in relevant)
                + "."
                if relevant
                else "Je ne connais aucun de tes anciens employeurs."
            )
            return self._result(answer, relevant)
        if query in self._likes_current_questions:
            relevant = self._current(facts, "likes")
            answer = (
                f"Tu aimes {_join_french([fact.object for fact in relevant])}."
                if relevant
                else "Je ne connais aucune de tes préférences actuelles."
            )
            return self._result(answer, relevant)
        if query in self._likes_history_questions:
            relevant = sorted(
                (
                    fact
                    for fact in facts
                    if fact.subject == "user"
                    and fact.predicate == "likes"
                    and (fact.retracted or not fact.is_current)
                    and not fact.conflict
                ),
                key=_timeline_key,
            )
            answer = (
                "Avant, tu aimais "
                + _join_french([fact.object for fact in relevant])
                + "."
                if relevant
                else "Je ne connais aucune de tes anciennes préférences."
            )
            return self._result(answer, relevant)
        return None

    @staticmethod
    def _result(
        answer: str,
        facts: list[LifecycleKnowledgeFact],
    ) -> dict:
        return {
            "answer": answer,
            "facts": [fact.model_dump(mode="json") for fact in facts],
            "reasoner": "deterministic_user_memory",
        }

    @staticmethod
    def _active_user(
        facts: list[LifecycleKnowledgeFact],
    ) -> list[LifecycleKnowledgeFact]:
        return [
            fact
            for fact in facts
            if (
                fact.subject == "user"
                or fact.predicate == "relation_to_user"
            )
            and fact.is_current
            and not fact.retracted
            and not fact.conflict
        ]

    @staticmethod
    def _current(
        facts: list[LifecycleKnowledgeFact],
        predicate: str,
    ) -> list[LifecycleKnowledgeFact]:
        return sorted(
            (
                fact
                for fact in facts
                if fact.subject == "user"
                and fact.predicate == predicate
                and fact.is_current
                and not fact.retracted
                and not fact.conflict
            ),
            key=lambda fact: fact.created_at,
        )

    @staticmethod
    def _timeline(
        facts: list[LifecycleKnowledgeFact],
        predicate: str,
    ) -> list[LifecycleKnowledgeFact]:
        timeline = sorted(
            (
                fact
                for fact in facts
                if fact.subject == "user"
                and fact.predicate == predicate
                and not fact.retracted
                and not fact.conflict
            ),
            key=_timeline_key,
        )
        return project_unique_timeline(timeline)

    def _profile(self, facts: list[LifecycleKnowledgeFact]) -> str:
        sentences: list[str] = []

        def current(predicate: str) -> LifecycleKnowledgeFact | None:
            values = self._current(facts, predicate)
            return values[-1] if values else None

        name = current("name")
        residence = current("lives_at")
        employer = current("works_at")
        spouse = current("spouse")
        children = self._current(facts, "has_child")
        likes = self._current(facts, "likes")

        if name:
            sentences.append(f"Tu t'appelles {name.object}.")
        if residence:
            sentences.append(
                f"Tu habites actuellement à {residence.object}."
            )
        if employer:
            sentences.append(f"Tu travailles chez {employer.object}.")
        if spouse:
            sentences.append(f"Ta femme s'appelle {spouse.object}.")
        if children:
            count = {
                1: "un",
                2: "deux",
                3: "trois",
                4: "quatre",
                5: "cinq",
            }.get(len(children), str(len(children)))
            sentences.append(
                f"Tu as {count} enfant{'s' if len(children) != 1 else ''} : "
                f"{_join_french([fact.object for fact in children])}."
            )
        if likes:
            sentences.append(
                f"Tu aimes {_join_french([fact.object for fact in likes])}."
            )
        return (
            " ".join(sentences)
            if sentences
            else "Je connais encore peu d’informations sur toi."
        )
