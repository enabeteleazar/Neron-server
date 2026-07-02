from __future__ import annotations

import pytest

from core.modules.memory import detect_memory_intent
from memory.oblivia import MemoryRecord, ObliviaMemoryManager


MEMORY_CASES = (
    ("J’ai un camion bleu.", "Quel est mon véhicule ?", "camion bleu"),
    ("Mon téléphone est un iPhone 17 Pro.", "Quel est mon smartphone ?", "iPhone 17 Pro"),
    ("Mon ordinateur portable est un ThinkPad.", "Quel est mon ordinateur portable ?", "ThinkPad"),
    ("Mon ordinateur fixe est un PC Ryzen.", "Quel est mon ordinateur fixe ?", "PC Ryzen"),
    ("Ma TV est une LG OLED.", "Quelle est ma TV ?", "LG OLED"),
    ("Ma montre est une Garmin.", "Quelle est ma montre ?", "Garmin"),
    ("Mon casque est un Sony XM6.", "Quel est mon casque ?", "Sony XM6"),
    ("Ma console est une PlayStation 6.", "Quelle est ma console ?", "PlayStation 6"),
    ("Mon NAS est un Synology.", "Quel est mon NAS ?", "Synology"),
    ("Mon imprimante est une Brother.", "Quelle est mon imprimante ?", "Brother"),
    ("Ma maison est à Nantes.", "Où est ma maison ?", "Nantes"),
    ("Mon toit est en ardoise.", "Quel est mon toit ?", "ardoise"),
    ("Mon portail est noir.", "De quelle couleur est mon portail ?", "noir"),
    ("Ma cuisine est blanche.", "De quelle couleur est ma cuisine ?", "blanche"),
    ("Mon salon est au rez-de-chaussée.", "Où est mon salon ?", "rez-de-chaussée"),
    ("Ma chambre est à l’étage.", "Où est ma chambre ?", "étage"),
    ("J’ai un chien labrador.", "Quel est mon animal ?", "chien labrador"),
    ("Mon chien s’appelle Rex.", "Comment s’appelle mon chien ?", "Rex"),
    ("Je travaille chez Constructel.", "Où est-ce que je travaille ?", "Constructel"),
    ("Ma box internet est une Freebox Ultra.", "Quelle est ma box internet ?", "Freebox Ultra"),
    ("Mon routeur est un Ubiquiti.", "Quel est mon routeur ?", "Ubiquiti"),
    ("Mon switch est un Netgear.", "Quel est mon switch ?", "Netgear"),
    ("Mon serveur est un Dell.", "Quel est mon serveur ?", "Dell"),
    ("Ma solution domotique est Home Assistant.", "Quelle est ma solution domotique ?", "Home Assistant"),
    ("Mon système de conteneurs est Docker.", "Quel système de conteneurs j’utilise ?", "Docker"),
    ("Mon système d’exploitation est Ubuntu.", "Quel est mon système d’exploitation ?", "Ubuntu"),
    ("Mon film préféré est Interstellar.", "Quel est mon film préféré ?", "Interstellar"),
    ("Mon jeu préféré est Zelda.", "Quel est mon jeu préféré ?", "Zelda"),
    ("Ma couleur préférée est le bleu.", "Quelle est ma couleur préférée ?", "bleu"),
)


@pytest.fixture
def manager(tmp_path):
    return ObliviaMemoryManager(
        sqlite_path=str(tmp_path / "memory.db"),
        obsidian_path=str(tmp_path / "obsidian"),
    )


@pytest.mark.parametrize("statement,question,expected", MEMORY_CASES)
def test_multidomain_personal_memory_recall(manager, statement, question, expected):
    remembered = manager.remember(MemoryRecord(content=statement))
    recalled = manager.recall_knowledge(question)

    assert remembered.metadata.get("facts"), statement
    assert recalled["facts"], question
    assert expected.casefold() in recalled["answer"].casefold()


@pytest.mark.parametrize("statement,question,expected", MEMORY_CASES)
def test_multidomain_statements_and_questions_route_to_memory(
    statement,
    question,
    expected,
):
    del expected
    assert detect_memory_intent(statement)["kind"] == "remember"
    assert detect_memory_intent(question)["kind"] == "recall"


def test_vehicle_color_and_phone_replacement_keep_latest_value(manager):
    for statement in (
        "J’ai un camion bleu.",
        "Mon camion est maintenant rouge.",
        "Mon téléphone est un iPhone 17 Pro.",
        "J’ai remplacé mon téléphone par un Pixel 10.",
    ):
        manager.remember(MemoryRecord(content=statement))

    vehicle = manager.recall_knowledge("Quel est mon véhicule ?")
    color = manager.recall_knowledge("De quelle couleur est mon camion ?")
    phone = manager.recall_knowledge("Quel est mon smartphone ?")

    assert "camion rouge" in vehicle["answer"].casefold()
    assert "rouge" in color["answer"].casefold()
    assert "pixel 10" in phone["answer"].casefold()
    assert "iphone" not in phone["answer"].casefold()
