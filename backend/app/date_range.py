"""Week/month range helpers shared by routers and CRUD.

Bounds are validated here because ``date + timedelta`` and ``calendar.monthrange``
raise on out-of-range input; letting that escape produces a 500 for a request
that is merely invalid.
"""

import calendar
from datetime import date, timedelta

MAX_WEEK_START = date(9998, 12, 31)


def week_bounds(week_start: date) -> tuple[date, date]:
    """Return (monday, sunday) for the given week start."""
    if week_start > MAX_WEEK_START:
        raise ValueError("week_start 超出可处理范围（最大 9998-12-31）")
    return week_start, week_start + timedelta(days=6)


def month_bounds(year: int, month: int) -> tuple[date, date]:
    """Return (first day, last day) of the given month."""
    try:
        last_day = calendar.monthrange(year, month)[1]
    except (calendar.IllegalMonthError, ValueError) as err:
        raise ValueError("year/month 超出可处理范围") from err
    return date(year, month, 1), date(year, month, last_day)
