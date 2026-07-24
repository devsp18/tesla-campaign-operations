"""
Quarterly completion report deadlines, 49 CFR 573.7(a).

Six consecutive quarters, or until corrective action is complete on all
affected vehicles, whichever comes first, starting with the calendar
quarter in which owner notification is sent. Each report is due on a
fixed calendar date after its quarter closes, rolled forward if that date
falls on a weekend or federal holiday.

Ported from the validated implementation in the companion project,
tesla-campaign-ops-toolkit (src/regulatory/clock.py), where it was checked
against the current CFR text and validated against real NHTSA filing
history. Kept here as a self-contained module rather than a cross-repo
import, since this project is deployed independently on Streamlit
Community Cloud.

MODELED USE. The owner notification date this module is anchored to is a
planning input a user sets, not an observed Tesla filing date, unless it
happens to equal one.
"""

from __future__ import annotations

import datetime as dt

import numpy as np
from pandas.tseries.holiday import USFederalHolidayCalendar

_QUARTER_DUE_MMDD = {1: (4, 30), 2: (7, 30), 3: (10, 30), 4: (1, 30)}
_holiday_cache: dict[tuple[int, int], np.ndarray] = {}


def _federal_holidays(start_year: int, end_year: int) -> np.ndarray:
    key = (start_year, end_year)
    if key not in _holiday_cache:
        cal = USFederalHolidayCalendar()
        holidays = cal.holidays(start=f"{start_year}-01-01", end=f"{end_year}-12-31")
        _holiday_cache[key] = holidays.values.astype("datetime64[D]")
    return _holiday_cache[key]


def _next_business_day(date_value: dt.date) -> dt.date:
    holidays = _federal_holidays(date_value.year, date_value.year + 1)
    result = np.busday_offset(
        np.datetime64(date_value, "D"), 0, roll="forward", holidays=holidays
    )
    return result.astype(dt.date)


def _calendar_quarter(date_value: dt.date) -> tuple[int, int]:
    return date_value.year, (date_value.month - 1) // 3 + 1


def _add_quarters(year: int, quarter: int, n: int) -> tuple[int, int]:
    zero_based = (year * 4 + (quarter - 1)) + n
    return zero_based // 4, zero_based % 4 + 1


def quarterly_due_dates(campaign_initiated_date: dt.date) -> list[dt.date]:
    """Six quarterly completion report due dates, 49 CFR 573.7(a), starting
    with the quarter containing campaign_initiated_date (the owner
    notification date)."""
    start_year, start_quarter = _calendar_quarter(campaign_initiated_date)
    due_dates = []
    for offset in range(6):
        year, quarter = _add_quarters(start_year, start_quarter, offset)
        due_year, _ = _add_quarters(year, quarter, 1)
        month, day = _QUARTER_DUE_MMDD[quarter]
        due_year_actual = due_year if quarter != 4 else year + 1
        raw_due = dt.date(due_year_actual, month, day)
        due_dates.append(_next_business_day(raw_due))
    return due_dates


def deadlines_with_status(
    notification_date: dt.date, weekly_cumulative: dict[int, float], total_affected: int
) -> list[dict]:
    """For each of the six quarterly deadlines, the due date, the rollout
    week it falls in (week 1 = the first week after notification), and
    whether cumulative completion had already reached the full affected
    population by that week ("cleared") or not ("at risk": that quarter's
    report would show a completion rate below 100%).

    weekly_cumulative maps week_number -> cumulative vehicles completed,
    for a single strategy's schedule.
    """
    results = []
    max_week = max(weekly_cumulative) if weekly_cumulative else 0
    for due in quarterly_due_dates(notification_date):
        week = (due - notification_date).days / 7
        week_floor = max(0, int(week))
        if week_floor <= 0:
            cumulative = 0
        elif week_floor >= max_week:
            cumulative = weekly_cumulative.get(max_week, 0)
        else:
            cumulative = weekly_cumulative.get(week_floor, 0)
        cleared = cumulative >= total_affected
        results.append({
            "due_date": due,
            "week": week,
            "cumulative": cumulative,
            "cleared": cleared,
        })
    return results
