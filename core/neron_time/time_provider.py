# neron_time/time_provider.py
from datetime import datetime
from zoneinfo import ZoneInfo

JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre"
]

class TimeProvider:
    def __init__(self, tz: str = "Europe/Paris"):
        self.tz = ZoneInfo(tz)

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def iso(self) -> str:
        return self.now().isoformat()

    def human(self) -> str:
        n = self.now()
        jour = JOURS[n.weekday()]
        mois = MOIS[n.month - 1]
        return f"{jour} {n.day} {mois} {n.year} a {n.hour:02d}h{n.minute:02d}"

    def timestamp(self) -> float:
        return self.now().timestamp()

    def date(self) -> str:
        return self.now().strftime("%d/%m/%Y")

    def time(self) -> str:
        return self.now().strftime("%H:%M:%S")
