from core.modules.timer import detect_timer_intent, build_timer_response


def test_detect_time_query():
    result = detect_timer_intent("Quelle heure est-il ?")
    assert result["matched"] is True
    assert result["kind"] == "time"


def test_detect_date_query():
    result = detect_timer_intent("Donne moi la date")
    assert result["matched"] is True
    assert result["kind"] == "date"


def test_timer_ignores_specialized_calendar_queries():
    result = detect_timer_intent("Donne-moi la date de Pâques 2027")
    assert result["matched"] is False


def test_build_time_response():
    result = build_timer_response("time")
    assert result["intent"] == "time_query"
    assert result["agent"] == "timer_module"
    assert "Il est" in result["response"]


def test_build_date_response():
    result = build_timer_response("date")
    assert result["intent"] == "time_query"
    assert result["agent"] == "timer_module"
    assert "Nous sommes le" in result["response"]
