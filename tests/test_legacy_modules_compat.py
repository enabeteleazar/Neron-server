from __future__ import annotations


def test_legacy_modules_scheduler_import_remains_compatible():
    from modules.scheduler import get_jobs
    from modules.scheduler import get_jobs as core_get_jobs

    assert get_jobs is core_get_jobs
