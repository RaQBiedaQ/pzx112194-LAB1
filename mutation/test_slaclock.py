# ai-generated: 85% - Claude wrote these tests from the docstrings of slaclock.py; the student reviewed them and ran `itsmlab mutants 5`
"""Behavioural tests for slaclock.py: every boundary written in a docstring has a test (P-29)."""
from datetime import datetime, timedelta

import pytest

from slaclock import (
    add_business_minutes,
    business_minutes_between,
    escalation_tier,
    is_business_time,
    parse_duration,
    priority_of,
    sla_state,
    targets,
)

# 2026-11-16 is a Monday.
MON = datetime(2026, 11, 16)
TUE = MON + timedelta(days=1)
WED = MON + timedelta(days=2)
FRI = MON + timedelta(days=4)
SAT = MON + timedelta(days=5)
SUN = MON + timedelta(days=6)
NEXT_MON = MON + timedelta(days=7)


def at(day, hour, minute=0, second=0, micro=0):
    return day.replace(hour=hour, minute=minute, second=second, microsecond=micro)


def weekdays_from(first, last):
    """Business days in [first, last] (dates), counted by brute force."""
    count = 0
    day = first
    while day <= last:
        if day.weekday() < 5:
            count += 1
        day += timedelta(days=1)
    return count


# ------------------------------------------------------------------ priority_of


@pytest.mark.parametrize(
    "impact, urgency, expected",
    [
        (1, 1, "P1"),
        (1, 2, "P2"), (2, 1, "P2"),
        (1, 3, "P3"), (2, 2, "P3"), (3, 1, "P3"),
        (2, 3, "P4"), (3, 2, "P4"), (3, 3, "P4"),
    ],
)
def test_priority_matrix(impact, urgency, expected):
    assert priority_of(impact, urgency) == expected
    assert priority_of(impact, urgency, False) == expected


@pytest.mark.parametrize(
    "impact, urgency, expected",
    [
        (1, 1, "P1"),
        (1, 2, "P2"), (2, 1, "P2"),
        (1, 3, "P2"), (2, 2, "P2"), (3, 1, "P2"),
        (2, 3, "P2"), (3, 2, "P2"), (3, 3, "P2"),
    ],
)
def test_priority_vip_is_never_below_p2(impact, urgency, expected):
    assert priority_of(impact, urgency, vip=True) == expected
    assert priority_of(impact, urgency, True) == expected


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, 1.0, True, False, "1", None, 10])
def test_priority_rejects_bad_impact(bad):
    with pytest.raises(ValueError):
        priority_of(bad, 1)
    with pytest.raises(ValueError):
        priority_of(bad, 2, vip=True)


@pytest.mark.parametrize("bad", [0, 4, -1, 2.0, 3.0, True, False, "1", None, 10])
def test_priority_rejects_bad_urgency(bad):
    with pytest.raises(ValueError):
        priority_of(1, bad)
    with pytest.raises(ValueError):
        priority_of(3, bad, vip=True)


def test_priority_returns_a_string():
    assert isinstance(priority_of(2, 2), str)


# ------------------------------------------------------------------ targets


@pytest.mark.parametrize(
    "priority, expected",
    [("P1", (15, 240)), ("P2", (60, 480)), ("P3", (240, 1440)), ("P4", (480, 4320))],
)
def test_targets_table(priority, expected):
    result = targets(priority)
    assert result == expected
    assert result[0] == expected[0]
    assert result[1] == expected[1]
    assert len(result) == 2


@pytest.mark.parametrize("bad", ["p1", " P1", "P1 ", "P5", "P0", "", "P", "1", "P11", "p4", None, 1])
def test_targets_lookup_is_exact(bad):
    with pytest.raises(ValueError):
        targets(bad)


# ------------------------------------------------------------------ sla_state


@pytest.mark.parametrize(
    "elapsed, target, expected",
    [
        (0, 15, "ok"), (1, 15, "ok"), (10, 15, "ok"), (11, 15, "ok"),
        (12, 15, "warning"), (13, 15, "warning"), (14, 15, "warning"), (15, 15, "warning"),
        (16, 15, "breached"), (100, 15, "breached"),
        (0, 100, "ok"), (74, 100, "ok"), (75, 100, "warning"), (76, 100, "warning"),
        (99, 100, "warning"), (100, 100, "warning"), (101, 100, "breached"),
        (0, 4, "ok"), (2, 4, "ok"), (3, 4, "warning"), (4, 4, "warning"), (5, 4, "breached"),
        (0, 1, "ok"), (1, 1, "warning"), (2, 1, "breached"),
        (0, 240, "ok"), (179, 240, "ok"), (180, 240, "warning"), (240, 240, "warning"), (241, 240, "breached"),
        (1439, 1440, "warning"), (1080, 1440, "warning"), (1079, 1440, "ok"), (1441, 1440, "breached"),
        (5, 8, "ok"), (6, 8, "warning"),
        (50, 4320, "ok"), (4320, 4320, "warning"), (4321, 4320, "breached"),
    ],
)
def test_sla_state(elapsed, target, expected):
    assert sla_state(elapsed, target) == expected


@pytest.mark.parametrize(
    "elapsed, target",
    [(-1, 15), (-100, 15), (0, 0), (5, 0), (0, -1), (5, -15), (-1, -1), (-1, 0)],
)
def test_sla_state_rejects_bad_arguments(elapsed, target):
    with pytest.raises(ValueError):
        sla_state(elapsed, target)


# ------------------------------------------------------------------ is_business_time


@pytest.mark.parametrize("day", [MON, TUE, WED, MON + timedelta(days=3), FRI])
def test_weekday_window_is_08_to_16_exclusive(day):
    assert is_business_time(at(day, 8, 0))
    assert is_business_time(at(day, 8, 1))
    assert is_business_time(at(day, 12, 0))
    assert is_business_time(at(day, 15, 59))
    assert not is_business_time(at(day, 7, 59))
    assert not is_business_time(at(day, 16, 0))
    assert not is_business_time(at(day, 16, 1))
    assert not is_business_time(at(day, 0, 0))
    assert not is_business_time(at(day, 23, 59))
    assert not is_business_time(at(day, 7, 0))
    assert not is_business_time(at(day, 17, 0))


@pytest.mark.parametrize("day", [SAT, SUN])
def test_weekend_is_never_business_time(day):
    for hour, minute in [(0, 0), (8, 0), (10, 30), (12, 0), (15, 59), (16, 0), (23, 59)]:
        assert not is_business_time(at(day, hour, minute))


def test_is_business_time_neighbouring_days():
    assert not is_business_time(at(SUN, 12, 0))
    assert is_business_time(at(MON, 12, 0))
    assert is_business_time(at(FRI, 12, 0))
    assert not is_business_time(at(SAT, 12, 0))


def test_is_business_time_returns_bool():
    assert is_business_time(at(MON, 9)) is True
    assert is_business_time(at(MON, 20)) is False
    assert is_business_time(at(SAT, 9)) is False


# ------------------------------------------------------------------ add_business_minutes


def test_add_zero_inside_hours_is_the_start():
    assert add_business_minutes(at(MON, 9, 0), 0) == at(MON, 9, 0)
    assert add_business_minutes(at(MON, 8, 0), 0) == at(MON, 8, 0)
    assert add_business_minutes(at(MON, 15, 59), 0) == at(MON, 15, 59)


def test_add_zero_outside_hours_is_the_next_opening():
    assert add_business_minutes(at(MON, 7, 0), 0) == at(MON, 8, 0)
    assert add_business_minutes(at(MON, 7, 59), 0) == at(MON, 8, 0)
    assert add_business_minutes(at(MON, 16, 0), 0) == at(TUE, 8, 0)
    assert add_business_minutes(at(MON, 20, 0), 0) == at(TUE, 8, 0)
    assert add_business_minutes(at(FRI, 16, 0), 0) == at(NEXT_MON, 8, 0)
    assert add_business_minutes(at(FRI, 23, 0), 0) == at(NEXT_MON, 8, 0)
    assert add_business_minutes(at(SAT, 10, 0), 0) == at(NEXT_MON, 8, 0)
    assert add_business_minutes(at(SUN, 12, 0), 0) == at(NEXT_MON, 8, 0)
    assert add_business_minutes(at(SAT, 0, 0), 0) == at(NEXT_MON, 8, 0)
    assert add_business_minutes(at(SUN, 23, 59), 0) == at(NEXT_MON, 8, 0)


def test_add_within_one_day():
    assert add_business_minutes(at(MON, 9, 0), 1) == at(MON, 9, 1)
    assert add_business_minutes(at(MON, 9, 0), 60) == at(MON, 10, 0)
    assert add_business_minutes(at(MON, 9, 30), 45) == at(MON, 10, 15)
    assert add_business_minutes(at(MON, 8, 0), 479) == at(MON, 15, 59)


def test_a_target_ending_exactly_at_closing_is_due_at_closing():
    assert add_business_minutes(at(MON, 9, 0), 420) == at(MON, 16, 0)
    assert add_business_minutes(at(MON, 8, 0), 480) == at(MON, 16, 0)
    assert add_business_minutes(at(FRI, 15, 0), 60) == at(FRI, 16, 0)
    assert add_business_minutes(at(MON, 15, 59), 1) == at(MON, 16, 0)


def test_one_minute_past_closing_rolls_to_the_next_business_day():
    assert add_business_minutes(at(MON, 9, 0), 421) == at(TUE, 8, 1)
    assert add_business_minutes(at(MON, 8, 0), 481) == at(TUE, 8, 1)
    assert add_business_minutes(at(FRI, 15, 0), 61) == at(NEXT_MON, 8, 1)
    assert add_business_minutes(at(MON, 15, 59), 2) == at(TUE, 8, 1)


def test_start_before_opening_moves_to_opening():
    assert add_business_minutes(at(MON, 7, 0), 30) == at(MON, 8, 30)
    assert add_business_minutes(at(MON, 7, 59), 1) == at(MON, 8, 1)
    assert add_business_minutes(at(MON, 0, 0), 480) == at(MON, 16, 0)
    assert add_business_minutes(at(MON, 7, 0), 481) == at(TUE, 8, 1)


def test_start_after_closing_moves_to_next_business_day():
    assert add_business_minutes(at(MON, 16, 0), 10) == at(TUE, 8, 10)
    assert add_business_minutes(at(MON, 17, 30), 10) == at(TUE, 8, 10)
    assert add_business_minutes(at(FRI, 16, 0), 10) == at(NEXT_MON, 8, 10)
    assert add_business_minutes(at(FRI, 17, 0), 30) == at(NEXT_MON, 8, 30)
    assert add_business_minutes(at(MON, 23, 59), 480) == at(TUE, 16, 0)


def test_start_on_a_weekend():
    assert add_business_minutes(at(SAT, 10, 0), 30) == at(NEXT_MON, 8, 30)
    assert add_business_minutes(at(SUN, 12, 0), 30) == at(NEXT_MON, 8, 30)
    assert add_business_minutes(at(SAT, 10, 0), 480) == at(NEXT_MON, 16, 0)
    assert add_business_minutes(at(SUN, 12, 0), 481) == at(NEXT_MON + timedelta(days=1), 8, 1)


def test_over_several_days_and_weekends():
    assert add_business_minutes(at(MON, 8, 0), 960) == at(TUE, 16, 0)
    assert add_business_minutes(at(MON, 9, 30), 1000) == at(WED, 10, 10)
    assert add_business_minutes(at(FRI, 8, 0), 481) == at(NEXT_MON, 8, 1)
    assert add_business_minutes(at(FRI, 8, 0), 960) == at(NEXT_MON, 16, 0)
    assert add_business_minutes(at(FRI, 8, 0), 961) == at(NEXT_MON + timedelta(days=1), 8, 1)
    assert add_business_minutes(at(MON, 8, 0), 2400) == at(FRI, 16, 0)
    assert add_business_minutes(at(MON, 8, 0), 2401) == at(NEXT_MON, 8, 1)
    assert add_business_minutes(at(MON, 8, 0), 4800) == at(NEXT_MON + timedelta(days=4), 16, 0)
    assert add_business_minutes(at(WED, 12, 0), 1440) == at(NEXT_MON, 12, 0)


def test_p_targets_in_business_time():
    # P3 resolution (1440 min = 3 business days) from Monday 10:00 is Thursday 10:00.
    assert add_business_minutes(at(MON, 10, 0), 1440) == at(MON + timedelta(days=3), 10, 0)
    # P1 resolution (240) from Friday 14:00: 120 on Friday, 120 on Monday.
    assert add_business_minutes(at(FRI, 14, 0), 240) == at(NEXT_MON, 10, 0)


def test_seconds_and_microseconds_of_the_start_are_ignored():
    assert add_business_minutes(at(MON, 9, 0, 45, 999), 60) == at(MON, 10, 0)
    assert add_business_minutes(at(MON, 15, 59, 59, 5), 1) == at(MON, 16, 0)
    assert add_business_minutes(at(MON, 9, 0, 0, 1), 0) == at(MON, 9, 0)
    assert add_business_minutes(at(MON, 7, 59, 59), 0) == at(MON, 8, 0)


def test_negative_minutes_are_rejected():
    with pytest.raises(ValueError):
        add_business_minutes(at(MON, 9, 0), -1)
    with pytest.raises(ValueError):
        add_business_minutes(at(SAT, 9, 0), -5)


def test_the_366_day_limit():
    start = at(MON, 8, 0)
    last_day = (MON + timedelta(days=366))
    assert last_day.weekday() < 5
    minutes = 480 * weekdays_from(MON, last_day)
    assert add_business_minutes(start, minutes) == at(last_day, 16, 0)
    assert add_business_minutes(start, minutes - 1) == at(last_day, 15, 59)
    with pytest.raises(ValueError):
        add_business_minutes(start, minutes + 1)
    with pytest.raises(ValueError):
        add_business_minutes(start, minutes + 5000)
    with pytest.raises(ValueError):
        add_business_minutes(start, 10 ** 7)


def test_the_limit_counts_from_the_date_of_the_start():
    start = at(MON, 15, 0)
    last_day = MON + timedelta(days=366)
    minutes = 60 + 480 * (weekdays_from(MON, last_day) - 1)
    assert add_business_minutes(start, minutes) == at(last_day, 16, 0)
    with pytest.raises(ValueError):
        add_business_minutes(start, minutes + 1)


def test_the_limit_from_a_weekend_start():
    start = at(SAT, 10, 0)
    last_day = SAT + timedelta(days=366)
    # SAT + 366 days is a Monday: the due date may still fall on it, not beyond.
    assert last_day.weekday() == 0
    minutes = 480 * weekdays_from(SAT, last_day)
    assert add_business_minutes(start, minutes) == at(last_day, 16, 0)
    with pytest.raises(ValueError):
        add_business_minutes(start, minutes + 1)


# ------------------------------------------------------------------ business_minutes_between


def test_between_same_moment_is_zero():
    assert business_minutes_between(at(MON, 9, 0), at(MON, 9, 0)) == 0
    assert business_minutes_between(at(MON, 7, 0), at(MON, 7, 0)) == 0
    assert business_minutes_between(at(SAT, 9, 0), at(SAT, 9, 0)) == 0


def test_between_inside_one_day():
    assert business_minutes_between(at(MON, 9, 0), at(MON, 10, 0)) == 60
    assert business_minutes_between(at(MON, 9, 0), at(MON, 9, 1)) == 1
    assert business_minutes_between(at(MON, 8, 0), at(MON, 16, 0)) == 480
    assert business_minutes_between(at(MON, 8, 0), at(MON, 15, 59)) == 479
    assert business_minutes_between(at(MON, 8, 1), at(MON, 16, 0)) == 479


def test_between_clips_to_business_hours():
    assert business_minutes_between(at(MON, 7, 0), at(MON, 9, 0)) == 60
    assert business_minutes_between(at(MON, 15, 0), at(MON, 17, 0)) == 60
    assert business_minutes_between(at(MON, 6, 0), at(MON, 20, 0)) == 480
    assert business_minutes_between(at(MON, 0, 0), at(MON, 7, 59)) == 0
    assert business_minutes_between(at(MON, 16, 0), at(MON, 23, 0)) == 0
    assert business_minutes_between(at(MON, 7, 0), at(MON, 8, 0)) == 0
    assert business_minutes_between(at(MON, 7, 0), at(MON, 8, 1)) == 1
    assert business_minutes_between(at(MON, 15, 59), at(MON, 17, 0)) == 1


def test_between_over_nights_and_weekends():
    assert business_minutes_between(at(MON, 9, 0), at(TUE, 9, 0)) == 480
    assert business_minutes_between(at(MON, 16, 0), at(TUE, 8, 0)) == 0
    assert business_minutes_between(at(MON, 15, 0), at(TUE, 9, 0)) == 120
    assert business_minutes_between(at(FRI, 15, 0), at(NEXT_MON, 9, 0)) == 120
    assert business_minutes_between(at(FRI, 16, 0), at(NEXT_MON, 8, 0)) == 0
    assert business_minutes_between(at(SAT, 10, 0), at(SUN, 10, 0)) == 0
    assert business_minutes_between(at(SAT, 10, 0), at(NEXT_MON, 8, 30)) == 30
    assert business_minutes_between(at(SUN, 12, 0), at(NEXT_MON, 8, 1)) == 1
    assert business_minutes_between(at(SAT, 0, 0), at(SUN, 23, 59)) == 0
    assert business_minutes_between(at(MON, 8, 0), at(NEXT_MON, 8, 0)) == 2400
    assert business_minutes_between(at(MON, 0, 0), at(NEXT_MON, 0, 0)) == 2400
    assert business_minutes_between(at(WED, 12, 0), at(NEXT_MON, 12, 0)) == 1440
    assert business_minutes_between(at(MON, 8, 0), at(WED, 16, 0)) == 1440


def test_between_seconds_are_ignored():
    assert business_minutes_between(at(MON, 9, 0, 59), at(MON, 9, 1, 30)) == 1
    assert business_minutes_between(at(MON, 9, 0, 0, 999), at(MON, 10, 0, 59, 5)) == 60
    assert business_minutes_between(at(MON, 9, 0, 59), at(MON, 9, 0, 10)) == 0
    assert business_minutes_between(at(MON, 15, 59, 59), at(MON, 16, 0, 59)) == 1


def test_between_end_before_start_is_rejected():
    with pytest.raises(ValueError):
        business_minutes_between(at(MON, 9, 1), at(MON, 9, 0))
    with pytest.raises(ValueError):
        business_minutes_between(at(TUE, 9, 0), at(MON, 9, 0))
    with pytest.raises(ValueError):
        business_minutes_between(at(SAT, 9, 1), at(SAT, 9, 0))
    with pytest.raises(ValueError):
        business_minutes_between(at(MON, 20, 0), at(MON, 7, 0))


def test_between_the_366_day_limit():
    start = at(MON, 8, 0)
    last_day = MON + timedelta(days=366)
    assert last_day.weekday() < 5
    expected = 480 * weekdays_from(MON, last_day)
    assert business_minutes_between(start, at(last_day, 16, 0)) == expected
    assert business_minutes_between(start, at(last_day, 23, 59)) == expected
    assert business_minutes_between(start, at(last_day, 0, 0)) == expected - 480
    next_day = at(last_day + timedelta(days=1), 0, 0)
    with pytest.raises(ValueError):
        business_minutes_between(start, next_day)
    with pytest.raises(ValueError):
        business_minutes_between(start, at(MON + timedelta(days=400), 12, 0))
    with pytest.raises(ValueError):
        business_minutes_between(at(MON, 23, 59), at(MON + timedelta(days=367), 0, 0))


def test_between_limit_counts_dates_not_elapsed_time():
    # 366 dates apart but fewer than 366 x 24 h elapsed: still allowed.
    start = at(MON, 23, 0)
    end = at(MON + timedelta(days=366), 1, 0)
    assert business_minutes_between(start, end) == 480 * (weekdays_from(MON, MON + timedelta(days=366)) - 2)
    # 367 dates apart but fewer than 367 x 24 h elapsed: rejected.
    with pytest.raises(ValueError):
        business_minutes_between(at(MON, 23, 0), at(MON + timedelta(days=367), 1, 0))


def test_between_inverts_add():
    starts = [
        at(MON, 8, 0), at(MON, 9, 17), at(MON, 15, 59), at(MON, 16, 0), at(MON, 7, 0),
        at(FRI, 15, 30), at(FRI, 17, 0), at(SAT, 10, 0), at(SUN, 12, 0), at(WED, 8, 1),
    ]
    for start in starts:
        for minutes in (0, 1, 59, 60, 479, 480, 481, 959, 960, 961, 2400, 2401, 5000, 12345):
            due = add_business_minutes(start, minutes)
            # The clock only runs while the window is open, so the elapsed business minutes are `minutes`.
            assert business_minutes_between(start, due) == minutes


def test_add_result_is_always_inside_or_at_the_end_of_business_hours():
    for minutes in range(0, 1300, 37):
        due = add_business_minutes(at(WED, 13, 41), minutes)
        assert due.weekday() < 5
        assert 8 * 60 <= due.hour * 60 + due.minute <= 16 * 60


# ------------------------------------------------------------------ escalation_tier


def expected_tier(priority, breached, reopens):
    tier = {"P1": 1, "P2": 1, "P3": 0, "P4": 0}[priority]
    if breached:
        tier += 2 if priority == "P1" else 1
    if reopens >= 2:
        tier += 1
    return min(tier, 3)


@pytest.mark.parametrize("priority", ["P1", "P2", "P3", "P4"])
@pytest.mark.parametrize("breached", [False, True])
@pytest.mark.parametrize("reopens", [0, 1, 2, 3, 10])
def test_escalation_matrix(priority, breached, reopens):
    assert escalation_tier(priority, breached, reopens) == expected_tier(priority, breached, reopens)


@pytest.mark.parametrize(
    "priority, breached, reopens, expected",
    [
        ("P1", False, 0, 1), ("P2", False, 0, 1), ("P3", False, 0, 0), ("P4", False, 0, 0),
        ("P1", True, 0, 3), ("P2", True, 0, 2), ("P3", True, 0, 1), ("P4", True, 0, 1),
        ("P1", False, 1, 1), ("P3", False, 1, 0), ("P3", False, 2, 1), ("P4", False, 2, 1),
        ("P2", False, 2, 2), ("P1", False, 2, 2), ("P3", True, 2, 2), ("P4", True, 1, 1),
        ("P2", True, 2, 3), ("P1", True, 1, 3), ("P1", True, 2, 3), ("P1", True, 99, 3),
    ],
)
def test_escalation_known_values(priority, breached, reopens, expected):
    assert escalation_tier(priority, breached, reopens) == expected


@pytest.mark.parametrize("priority", ["p1", "P5", "P0", "", " P1", "P1 ", None, "1"])
def test_escalation_rejects_unknown_priority(priority):
    with pytest.raises(ValueError):
        escalation_tier(priority, False, 0)
    with pytest.raises(ValueError):
        escalation_tier(priority, True, 3)


@pytest.mark.parametrize("priority", ["P1", "P2", "P3", "P4"])
def test_escalation_rejects_negative_reopens(priority):
    with pytest.raises(ValueError):
        escalation_tier(priority, False, -1)
    with pytest.raises(ValueError):
        escalation_tier(priority, True, -5)


def test_escalation_is_an_int_and_capped():
    result = escalation_tier("P1", True, 5)
    assert isinstance(result, int)
    assert result == 3
    assert max(escalation_tier(p, b, r) for p in ("P1", "P2", "P3", "P4") for b in (False, True) for r in range(6)) == 3


# ------------------------------------------------------------------ parse_duration


@pytest.mark.parametrize(
    "text, expected",
    [
        ("1m", 1), ("5m", 5), ("59m", 59), ("60m", 60), ("90m", 90), ("120m", 120), ("1000m", 1000),
        ("1h", 60), ("4h", 240), ("24h", 1440), ("100h", 6000),
        ("1d", 1440), ("2d", 2880), ("10d", 14400),
        ("1h1m", 61), ("1h30m", 90), ("1h59m", 119), ("2h5m", 125),
        ("1d4h", 1680), ("1d1h", 1500), ("2d3h4m", 3064), ("1d0h5m", 1445), ("1d5m", 1445), ("1d59m", 1499),
        ("0h60m", 60), ("0h61m", 61), ("0d90m", 90), ("0d0h120m", 120), ("0d1m", 1), ("0d0h1m", 1),
        ("0d1h", 60),
    ],
)
def test_parse_duration_valid(text, expected):
    if expected is None:
        with pytest.raises(ValueError):
            parse_duration(text)
    else:
        assert parse_duration(text) == expected


@pytest.mark.parametrize("text", [" 90m", "90m ", "  1h30m  ", "\t2d\n", "\n4h", " 1d4h "])
def test_parse_duration_ignores_surrounding_whitespace(text):
    assert parse_duration(text) == parse_duration(text.strip())
    assert parse_duration(text) > 0


@pytest.mark.parametrize(
    "text",
    [
        "", " ", "   ", "0m", "0h", "0d", "0d0h0m", "00m", "0h0m", "0d0m",
        "1.5h", "30m1h", "1h2d", "4h1d", "-5m", "+5m", "1 h", "1h 30m", "1d 4h", "1H", "1D", "1M", "1h30M",
        "5", "m", "h", "d", "hm", "1hm", "h1", "1h1h", "1m1m", "1d1d", "1d2h3m4m", "abc", "1x", "1s", "1w",
        "1h60m", "1h61m", "1h99m", "1d60m", "1d1h60m", "2d0h60m", "5h120m",
        "1,5h", "1h,30m", "1h-30m", "1h+30m", "1h30", "h30m", "d4h", "1d-1h",
    ],
)
def test_parse_duration_invalid(text):
    with pytest.raises(ValueError):
        parse_duration(text)


def test_parse_duration_is_positive_and_int():
    value = parse_duration("1d1h1m")
    assert value == 1501
    assert isinstance(value, int)


def test_parse_duration_parts_are_independent():
    assert parse_duration("1d") + parse_duration("1h") + parse_duration("1m") == parse_duration("1d1h1m")
    assert parse_duration("3d") == 3 * 1440
    assert parse_duration("3h") == 3 * 60
    assert parse_duration("3m") == 3
    assert parse_duration("7d11h13m") == 7 * 1440 + 11 * 60 + 13
