import pytest

from core.app import _start_scheduler, _stop_scheduler


class SchedulerStub:
    def __init__(self) -> None:
        self.start_worker_calls = 0
        self.stop_worker_calls = 0
        self.start_calls = 0
        self.stop_calls = 0
        self.recovered_tasks = []

    def recover_running_tasks(self):
        return self.recovered_tasks

    async def start_worker(self) -> None:
        self.start_worker_calls += 1

    async def stop_worker(self) -> None:
        self.stop_worker_calls += 1

    def start(self) -> None:
        self.start_calls += 1

    def stop(self) -> None:
        self.stop_calls += 1


@pytest.mark.asyncio
async def test_scheduler_helpers_prefer_worker_api() -> None:
    scheduler = SchedulerStub()

    await _start_scheduler(scheduler)
    await _stop_scheduler(scheduler)

    assert scheduler.start_worker_calls == 1
    assert scheduler.stop_worker_calls == 1
    assert scheduler.start_calls == 0
    assert scheduler.stop_calls == 0
