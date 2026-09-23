"""The judge-facing report must fail unless every proof condition is exact."""
from app.race_demo import Outcome, require_local_url, summarize


def test_summary_accepts_one_winner_and_forty_nine_clean_conflicts():
    outcomes = [Outcome(201)] + [Outcome(409, "SLOT_ALREADY_BOOKED") for _ in range(49)]
    summary = summarize(outcomes, database_confirmed=1, elapsed=0.5)
    assert summary.passed
    assert summary.oversold == 0
    assert summary.requests == 50


def test_summary_rejects_wrong_conflict_or_multiple_database_rows():
    outcomes = [Outcome(201), Outcome(409, "SLOT_UNAVAILABLE")]
    summary = summarize(outcomes, database_confirmed=2, elapsed=0.5)
    assert not summary.passed
    assert summary.unexpected_responses == 1
    assert summary.oversold == 1


def test_race_demo_accepts_only_loopback_api_urls():
    assert require_local_url("http://localhost:8000/") == "http://localhost:8000"
    try:
        require_local_url("https://example.com")
    except ValueError as exc:
        assert "local" in str(exc)
    else:
        raise AssertionError("Non-local race target was accepted")
