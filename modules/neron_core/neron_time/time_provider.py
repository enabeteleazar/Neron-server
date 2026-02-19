# neron_time/time_provider.py
from datetime import datetime
from zoneinfo import ZoneInfo


class TimeProvider:
    def __init__(self, tz: str = "Europe/Paris"):
        self.tz = ZoneInfo(tz)

    def now(self) -> datetime:
        return datetime.now(self.tz)

    def iso(self) -> str:
        return self.now().isoformat()

    def human(self) -> str:
        return self.now().strftime("%A %d %B %Y a %Hh%M")

    def timestamp(self) -> float:
        return self.now().timestamp()

    def date(self) -> str:
        return self.now().strftime("%d/%m/%Y")

    def time(self) -> str:
        return self.now().strftime("%H:%M:%S")
