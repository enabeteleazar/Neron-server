from __future__ import annotations

from integrations.homeassistant.helpers import detect_domain, normalize, similarity, tokens
from integrations.homeassistant.types import HAMatch, HAState


class EntitySearch:
    def __init__(self, states: list[HAState], aliases: dict[str, list[str]] | None = None) -> None:
        self.states = states
        self.aliases = aliases or {}

    def search(self, query: str, *, domain: str | None = None, limit: int = 5) -> list[HAMatch]:
        wanted_domain = domain or detect_domain(query)
        query_tokens = set(tokens(query))
        matches: list[HAMatch] = []
        for state in self.states:
            if wanted_domain and state.domain != wanted_domain:
                continue
            haystacks = self._haystacks(state)
            score = 0.0
            reasons: list[str] = []
            for haystack in haystacks:
                hay_tokens = set(tokens(haystack))
                overlap = len(query_tokens & hay_tokens)
                if overlap:
                    score += overlap * 3
                    reasons.append("token_overlap")
                fuzzy = similarity(query, haystack)
                if fuzzy >= 0.45:
                    score += fuzzy * 4
                    reasons.append("similarity")
            if wanted_domain:
                score += 1
                reasons.append("domain")
            if score > 0:
                matches.append(HAMatch(
                    entity_id=state.entity_id,
                    score=round(score, 3),
                    name=state.friendly_name,
                    domain=state.domain,
                    state=state.state,
                    reasons=sorted(set(reasons)),
                ))
        return sorted(matches, key=lambda item: item.score, reverse=True)[:limit]

    def best(self, query: str, *, domain: str | None = None) -> HAMatch | None:
        matches = self.search(query, domain=domain, limit=1)
        return matches[0] if matches else None

    def _haystacks(self, state: HAState) -> list[str]:
        alias_values = self.aliases.get(state.entity_id, [])
        area = str(state.attributes.get("area") or state.attributes.get("area_id") or "")
        floor = str(state.attributes.get("floor") or state.attributes.get("floor_id") or "")
        return [
            state.entity_id,
            state.entity_id.replace(".", " ").replace("_", " "),
            state.friendly_name,
            area,
            floor,
            *map(str, alias_values),
        ]
