from __future__ import annotations


def test_status_module_is_importable_and_builds_summary(monkeypatch):
    import core.status as status

    monkeypatch.setattr(
        status,
        "_get_status",
        lambda: {"cpu_pct": 12, "ram_pct": 34, "disk_pct": 56, "process_ram_mb": 78},
    )
    monkeypatch.setattr(status, "get_health_score", lambda: {"score": 91, "level": "healthy"})
    monkeypatch.setattr(
        status,
        "get_jobs",
        lambda: [{"name": "daily", "next_run": "2026-06-02T21:00:00+02:00"}],
    )

    data = status.check_all_improved()
    summary = status.get_summary_text()

    assert data["system"]["cpu_pct"] == 12
    assert data["health"]["score"] == 91
    assert data["jobs"] == [{"name": "daily", "next_run": "2026-06-02T21:00"}]
    assert "healthy" in summary
    assert "daily" in summary
