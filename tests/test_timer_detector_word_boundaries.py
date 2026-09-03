"""Le detecteur timer ne doit pas confondre « bonjour » avec « jour ».

Il testait l'appartenance de SOUS-CHAINES : `"jour" in value` attrapait
« bonjour », « bonne journee », « toujours », « sejour », « journal », et
`"heure" in value` attrapait « malheureusement ».

L'orchestrateur consulte ce detecteur AVANT la branche conversation
(orchestrator.py:359 — `timer_result.get("matched")` suffit a router vers
`timer_engine`). Consequence mesuree en production le 03/09/2026 : dire
« Bonjour » a Neron lui faisait repondre « Nous sommes le 03/09/2026 ».

Le classifieur ML n'etait pas en cause : il classait bien « Dis bonjour en
trois mots » en CONVERSATION. C'est ce detecteur qui le court-circuitait.
"""

from __future__ import annotations

import pytest

from core.modules.timer.detector import detect_timer_intent


@pytest.mark.parametrize(
    "phrase",
    [
        "Bonjour",
        "Bonjour Neron",
        "Dis bonjour en trois mots",
        "Bonne journee",
        "Lis le journal des erreurs",
        "Il y a toujours un souci",
        "Raconte mon sejour a Paris",
        "Malheureusement ca ne marche pas",
        "Fais une mise a jour du systeme",
    ],
)
def test_words_merely_containing_jour_or_heure_are_not_dates(phrase):
    assert detect_timer_intent(phrase)["matched"] is False, phrase


@pytest.mark.parametrize(
    "phrase",
    [
        "Quelle heure est-il ?",
        "Il est quelle heure",
        "Donne moi la date",
        "On est quel jour ?",
        "Quelle est la date du jour",
        "aujourd'hui",
    ],
)
def test_real_time_and_date_questions_still_match(phrase):
    assert detect_timer_intent(phrase)["matched"] is True, phrase
