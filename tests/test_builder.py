# tests/test_builder.py
"""
Tests unitaires — world_model/builder.py (fonctions pures)
Couvre : _status, _anomaly_severity, _compute_global_score,
         _compute_confidence, _build_recommendations.
"""

import pytest
from core.memory.world_model.builder import (
    _status,
    _anomaly_severity,
    _compute_global_score,
    _compute_confidence,
    _build_recommendations,
)


# ── _status ────────────────────────────────────────────────────────────────────

class TestStatus:
    def test_normal(self):
        assert _status(50.0, 80.0) == "normal"

    def test_degraded_at_warn(self):
        assert _status(80.0, 80.0) == "degraded"

    def test_degraded_above_warn(self):
        assert _status(85.0, 80.0) == "degraded"

    def test_critical_at_crit(self):
        assert _status(90.0, 80.0, 90.0) == "critical"

    def test_critical_above_crit(self):
        assert _status(95.0, 80.0, 90.0) == "critical"

    def test_degraded_between_warn_and_crit(self):
        assert _status(85.0, 80.0, 90.0) == "degraded"

    def test_no_crit_threshold(self):
        assert _status(99.0, 80.0) == "degraded"
        assert _status(10.0, 80.0) == "normal"


# ── _anomaly_severity ──────────────────────────────────────────────────────────

class TestAnomalySeverity:
    @pytest.mark.parametrize("anomaly_type", [
        "cascade", "crash_after_restart", "memory_leak_pattern",
    ])
    def test_high_severity(self, anomaly_type):
        assert _anomaly_severity(anomaly_type) == "high"

    @pytest.mark.parametrize("anomaly_type", [
        "cpu_spike", "disk_warning", "timeout", "unknown", "",
    ])
    def test_medium_severity(self, anomaly_type):
        assert _anomaly_severity(anomaly_type) == "medium"


# ── _compute_global_score ──────────────────────────────────────────────────────

class TestComputeGlobalScore:
    def _make_system(self, cpu=10, ram=10, disk=10):
        return {
            "cpu":  {"current": cpu},
            "ram":  {"current": ram},
            "disk": {"usage":   disk},
        }

    def _make_agents(self, score=100):
        return {"score": {"global": score, "level": "healthy"}}

    def test_healthy_baseline(self):
        result = _compute_global_score(
            self._make_system(), self._make_agents(), []
        )
        assert result["score"] == 100.0
        assert result["level"] == "healthy"

    def test_cpu_above_80(self):
        result = _compute_global_score(
            self._make_system(cpu=85), self._make_agents(), []
        )
        assert result["score"] == 90.0

    def test_cpu_above_90(self):
        result = _compute_global_score(
            self._make_system(cpu=95), self._make_agents(), []
        )
        assert result["score"] == 80.0  # -10 (>80) -10 (>90)

    def test_ram_above_85(self):
        result = _compute_global_score(
            self._make_system(ram=90), self._make_agents(), []
        )
        assert result["score"] == 90.0

    def test_disk_above_90(self):
        result = _compute_global_score(
            self._make_system(disk=92), self._make_agents(), []
        )
        assert result["score"] == 85.0

    def test_agent_score_caps_global(self):
        result = _compute_global_score(
            self._make_system(), self._make_agents(score=60), []
        )
        assert result["score"] == 60.0

    def test_high_anomaly_penalty(self):
        anomalies = [{"severity": "high", "message": "crash"}]
        result = _compute_global_score(
            self._make_system(), self._make_agents(), anomalies
        )
        assert result["score"] == 85.0

    def test_medium_anomaly_penalty(self):
        anomalies = [{"severity": "medium", "message": "disk"}]
        result = _compute_global_score(
            self._make_system(), self._make_agents(), anomalies
        )
        assert result["score"] == 95.0

    def test_score_clamped_to_0(self):
        anomalies = [{"severity": "high"}] * 20
        result = _compute_global_score(
            self._make_system(cpu=99, ram=99, disk=99),
            self._make_agents(score=0),
            anomalies,
        )
        assert result["score"] == 0.0

    def test_score_clamped_to_100(self):
        result = _compute_global_score(
            self._make_system(), self._make_agents(score=200), []
        )
        assert result["score"] <= 100.0

    @pytest.mark.parametrize("score,expected_level", [
        (95.0, "healthy"),
        (90.0, "healthy"),
        (80.0, "degraded"),
        (70.0, "degraded"),
        (60.0, "warning"),
        (50.0, "warning"),
        (49.0, "critical"),
        (0.0,  "critical"),
    ])
    def test_level_thresholds(self, score, expected_level):
        agents = {"score": {"global": score}}
        result = _compute_global_score(self._make_system(), agents, [])
        assert result["level"] == expected_level

    def test_trend_is_stable(self):
        result = _compute_global_score(
            self._make_system(), self._make_agents(), []
        )
        assert result["trend"] == "stable"


# ── _compute_confidence ────────────────────────────────────────────────────────

class TestComputeConfidence:
    def test_full_confidence(self):
        assert _compute_confidence({}, {}) == 1.0

    def test_system_error_reduces_confidence(self):
        c = _compute_confidence({"error": "psutil failed"}, {})
        assert c == pytest.approx(0.7)

    def test_agents_error_reduces_confidence(self):
        c = _compute_confidence({}, {"error": "watchdog down"})
        assert c == pytest.approx(0.7)

    def test_both_errors_reduces_confidence(self):
        c = _compute_confidence({"error": "e1"}, {"error": "e2"})
        assert c == pytest.approx(0.4)

    def test_confidence_never_below_0(self):
        c = _compute_confidence({"error": "e"}, {"error": "e"})
        assert c >= 0.0


# ── _build_recommendations ─────────────────────────────────────────────────────

class TestBuildRecommendations:
    def _sys(self, cpu=10, ram=10, disk=10):
        return {
            "cpu":  {"current": cpu},
            "ram":  {"current": ram},
            "disk": {"usage":   disk},
        }

    def test_no_recommendations_baseline(self):
        recs = _build_recommendations(self._sys(), {}, [])
        assert recs == []

    def test_cpu_high_recommendation(self):
        recs = _build_recommendations(self._sys(cpu=90), {}, [])
        actions = [r["action"] for r in recs]
        assert "monitor_cpu" in actions

    def test_cpu_high_priority(self):
        recs = _build_recommendations(self._sys(cpu=92), {}, [])
        cpu_rec = next(r for r in recs if r["action"] == "monitor_cpu")
        assert cpu_rec["priority"] == "high"

    def test_cpu_medium_priority(self):
        recs = _build_recommendations(self._sys(cpu=86), {}, [])
        cpu_rec = next(r for r in recs if r["action"] == "monitor_cpu")
        assert cpu_rec["priority"] == "medium"

    def test_ram_recommendation(self):
        recs = _build_recommendations(self._sys(ram=90), {}, [])
        actions = [r["action"] for r in recs]
        assert "check_memory" in actions

    def test_disk_recommendation(self):
        recs = _build_recommendations(self._sys(disk=90), {}, [])
        actions = [r["action"] for r in recs]
        assert "free_disk_space" in actions

    def test_disk_high_priority(self):
        recs = _build_recommendations(self._sys(disk=95), {}, [])
        disk_rec = next(r for r in recs if r["action"] == "free_disk_space")
        assert disk_rec["priority"] == "high"

    def test_anomaly_recommendation(self):
        anomalies = [{"severity": "high", "message": "crash détecté"}]
        recs = _build_recommendations(self._sys(), {}, anomalies)
        assert any(r["action"] == "investigate_anomaly" for r in recs)

    def test_medium_anomaly_no_recommendation(self):
        anomalies = [{"severity": "medium", "message": "cpu spike"}]
        recs = _build_recommendations(self._sys(), {}, anomalies)
        assert not any(r["action"] == "investigate_anomaly" for r in recs)

    def test_multiple_issues(self):
        recs = _build_recommendations(self._sys(cpu=90, ram=90, disk=90), {}, [])
        actions = {r["action"] for r in recs}
        assert "monitor_cpu" in actions
        assert "check_memory" in actions
        assert "free_disk_space" in actions


# ── constants : sanity checks ──────────────────────────────────────────────────

class TestConstants:
    def test_all_lists_non_empty(self):
        from core.constants import (
            CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
            WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS,
        )
        for lst in [CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
                    WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS]:
            assert len(lst) > 0

    def test_all_keywords_are_strings(self):
        from core.constants import (
            CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
            WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS,
        )
        for lst in [CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
                    WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS]:
            for kw in lst:
                assert isinstance(kw, str), f"Non-string keyword: {kw!r}"

    def test_no_empty_keywords(self):
        from core.constants import (
            CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
            WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS,
        )
        for lst in [CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
                    WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS]:
            for kw in lst:
                assert kw.strip() != "", f"Empty keyword found in list"

    def test_no_duplicates_within_list(self):
        from core.constants import (
            CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
            WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS,
        )
        for lst in [CODE_KEYWORDS, CODE_AUDIT_KEYWORDS, HA_KEYWORDS,
                    WEB_KEYWORDS, TIME_KEYWORDS, PERSONALITY_KEYWORDS]:
            assert len(lst) == len(set(lst)), "Duplicate keyword detected"
