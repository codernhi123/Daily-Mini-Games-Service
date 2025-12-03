from __future__ import annotations
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, date, timezone
from statistics import mean, median
from typing import Dict, List, Tuple

from .models.event import Event


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p
    f = int(k)
    c = min(f + 1, len(s) - 1)
    if f == c:
        return float(s[int(k)])
    return float(s[f] * (c - k) + s[c] * (k - f))


@dataclass
class DayStats:
    session_lengths: List[float]
    active_at_end: int
    max_active: int


def build_sessions_for_day(events: List[Event], auth_ttl: int, day: date) -> DayStats:
    ttl = timedelta(seconds=auth_ttl)
    start = datetime.combine(day, datetime.min.time()).replace(microsecond=0, tzinfo = timezone.utc) #
    end = datetime.combine(day, datetime.max.time()).replace(microsecond=0, tzinfo = timezone.utc)

    per_user: Dict[str, List[datetime]] = defaultdict(list)
    for e in events:
        if e.user is not None:
            per_user[e.user].append(e.when)
    for u in per_user:
        per_user[u].sort()

    # merge ≤ ttl gaps into sessions
    intervals: List[Tuple[datetime, datetime]] = []
    for _, times in per_user.items():
        if not times:
            continue
        a = times[0]
        b = times[0] + ttl
        for t in times[1:]:
            if t <= b:
                b = max(b, t + ttl)
            else:
                intervals.append((a, b))
                a, b = t, t + ttl
        intervals.append((a, b))

    # clamp to the day
    lengths: List[float] = []
    clamped: List[Tuple[datetime, datetime]] = []
    for A, B in intervals:
        A2 = max(A, start)
        B2 = min(B, end)
        if A2 < B2:
            clamped.append((A2, B2))
            lengths.append((B2 - A2).total_seconds())

    # active users at day end
    cutoff = end
    active_end = 0
    for _, times in per_user.items():
        import bisect
        i = bisect.bisect_right(times, cutoff) - 1
        if i >= 0 and times[i] + ttl > cutoff:
            active_end += 1

    # max concurrent active (line sweep)
    points: List[Tuple[datetime, int]] = []
    for A, B in clamped:
        points.append((A, +1))
        points.append((B, -1))
    points.sort()
    cur = 0
    max_active = 0
    for _, d in points:
        cur += d
        max_active = max(max_active, cur)

    return DayStats(session_lengths=lengths, active_at_end=active_end, max_active=max_active)


def summarize_day(stats: DayStats) -> dict:
    L = stats.session_lengths
    return {
        "session_length": {
            "min": min(L) if L else 0.0,
            "max": max(L) if L else 0.0,
            "mean": mean(L) if L else 0.0,
            "median": median(L) if L else 0.0,
            "p95": _percentile(L, 0.95) if L else 0.0,
        },
        "active_users": {
            "current": stats.active_at_end,
            "max": stats.max_active,
        },
    }


def average_reports(reports: List[dict]) -> dict:
    if not reports:
        return {
            "session_length": {"min": 0.0, "max": 0.0, "mean": 0.0, "median": 0.0, "p95": 0.0},
            "active_users": {"current": 0.0, "max": 0.0},
        }
    n = len(reports)
    def avg(path):
        s = 0.0
        for r in reports:
            x = r
            for k in path:
                x = x[k]
            s += float(x)
        return s / n
    return {
        "session_length": {
            "min":  avg(["session_length", "min"]),
            "max":  avg(["session_length", "max"]),
            "mean": avg(["session_length", "mean"]),
            "median": avg(["session_length", "median"]),
            "p95":  avg(["session_length", "p95"]),
        },
        "active_users": {
            "current": avg(["active_users", "current"]),
            "max":     avg(["active_users", "max"]),
        },
    }
