# src/user_service/test_analytics.py

from datetime import datetime, date, timedelta, timezone

from user_service import analytics


class _E:
    """simple fake event with .when and .user"""
    def __init__(self, when, user):
        self.when = when
        self.user = user


def test_percentile_empty_and_nonempty():
    assert analytics._percentile([], 0.95) == 0.0
    assert analytics._percentile([1.0], 0.95) == 1.0
    # sorted = [1, 2, 10]
    v = analytics._percentile([10.0, 1.0, 2.0], 0.5)
    assert 1.9 <= v <= 2.1  # around the middle


def test_build_sessions_for_day_and_summarize():
    day = date(2025, 10, 15)
    base = datetime(2025, 10, 15, 10, 0, 0, tzinfo = timezone.utc)

    events = [
        _E(base, "u1"),
        _E(base + timedelta(seconds=100), "u1"),  # within ttl → same session
        _E(base + timedelta(hours=2), "u2"),
    ]

    stats = analytics.build_sessions_for_day(
        events=events,
        auth_ttl=300,
        day=day,
    )

    assert stats.session_lengths
    # we don't expect anyone to still be active at 23:59
    assert isinstance(stats.active_at_end, int)
    assert stats.active_at_end >= 0
    assert stats.max_active >= 1

    summary = analytics.summarize_day(stats)
    assert "session_length" in summary
    assert "active_users" in summary


def test_average_reports_with_data_and_empty():
    empty = analytics.average_reports([])
    assert empty["session_length"]["mean"] == 0.0

    r1 = {
        "session_length": {"min": 10, "max": 30, "mean": 20, "median": 20, "p95": 30},
        "active_users": {"current": 2, "max": 3},
    }
    r2 = {
        "session_length": {"min": 20, "max": 40, "mean": 30, "median": 30, "p95": 40},
        "active_users": {"current": 4, "max": 5},
    }

    avg = analytics.average_reports([r1, r2])
    # each field should be averaged
    assert avg["session_length"]["min"] == (10 + 20) / 2
    assert avg["active_users"]["current"] == (2 + 4) / 2

def test_percentile_interpolates_between_points():
    # sorted → [1, 3, 9, 10]
    vals = [10.0, 1.0, 9.0, 3.0]
    # len=4 → indexes 0..3
    # p=0.25 → k = 0.75 → f=0, c=1 → interpolate between 1 and 3
    v = analytics._percentile(vals, 0.25)
    assert 1.0 < v < 3.0


def test_build_sessions_for_day_clamps_to_day_and_ignores_none_user():
    day = date(2025, 10, 15)
    # make a session that STARTS the previous day and ends this day
    prev_night = datetime(2025, 10, 14, 23, 50, 0, tzinfo = timezone.utc)
    same_day = datetime(2025, 10, 15, 0, 5, 0, tzinfo = timezone.utc)

    events = [
        _E(prev_night, "u1"),
        _E(same_day, "u1"),
        _E(datetime(2025, 10, 15, 12, 0, 0, tzinfo = timezone.utc), None),  # should not break anything
    ]

    stats = analytics.build_sessions_for_day(
        events=events,
        auth_ttl=600,  # 10 minutes
        day=day,
    )

    # because of clamping, we should have exactly one session, nonzero length
    assert len(stats.session_lengths) == 1
    assert stats.session_lengths[0] > 0
    # we should also have some active_at_end/max_active computed
    assert isinstance(stats.active_at_end, int)
    assert isinstance(stats.max_active, int)


def test_build_sessions_for_day_no_events():
    day = date(2025, 10, 15)
    stats = analytics.build_sessions_for_day(
        events=[],
        auth_ttl=300,
        day=day,
    )
    assert stats.session_lengths == []
    summary = analytics.summarize_day(stats)
    assert summary["session_length"]["min"] == 0.0
    assert summary["active_users"]["current"] == 0


def test_average_reports_every_field_is_averaged():
    reports = [
        {
            "session_length": {
                "min": 5.0,
                "max": 10.0,
                "mean": 7.0,
                "median": 7.0,
                "p95": 10.0,
            },
            "active_users": {"current": 1, "max": 3},
        },
        {
            "session_length": {
                "min": 15.0,
                "max": 20.0,
                "mean": 17.0,
                "median": 17.0,
                "p95": 20.0,
            },
            "active_users": {"current": 5, "max": 7},
        },
    ]

    avg = analytics.average_reports(reports)
    # prove each path was walked
    assert avg["session_length"]["min"] == (5.0 + 15.0) / 2.0
    assert avg["session_length"]["p95"] == (10.0 + 20.0) / 2.0
    assert avg["active_users"]["max"] == (3 + 7) / 2.0