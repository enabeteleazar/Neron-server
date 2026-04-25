"""Agent déterministe: timer
Fournit utilitaires temps/heure indépendants.
"""
from datetime import datetime


def time():
    now = datetime.now()
    return now.strftime("%H:%M")


def human():
    now = datetime.now()
    return now.strftime("%d/%m/%Y")


def tick():
    return {"ok": True, "msg": "timer tick", "time": time(), "date": human()}
