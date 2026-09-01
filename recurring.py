"""Date helpers for annually recurring podcast episodes."""

from datetime import datetime


def _date_in_year(release_date: datetime, year: int) -> datetime:
    """Move a date to ``year``, preserving local wall time across DST."""
    try:
        naive_occurrence = release_date.replace(year=year, tzinfo=None)
    except ValueError:
        if release_date.month == 2 and release_date.day == 29:
            naive_occurrence = release_date.replace(year=year, day=28, tzinfo=None)
        else:
            raise

    if release_date.tzinfo is None:
        return naive_occurrence

    # pytz requires localize() to select the offset applicable in the target
    # year. A direct datetime.replace(year=...) can retain an obsolete DST
    # offset even though the intended local release time is unchanged.
    localize = getattr(release_date.tzinfo, "localize", None)
    if callable(localize):
        return localize(naive_occurrence)

    return naive_occurrence.replace(tzinfo=release_date.tzinfo)


def effective_annual_release_date(
    release_date: datetime,
    current_time: datetime,
) -> datetime:
    """Return the latest occurrence of an annually recurring release.

    The database date is a stable month/day/time recurrence anchor. Once that
    anniversary arrives, the returned date advances to the current year. Until
    then, it remains on the previous year's occurrence so RSS feeds do not
    publish future-dated episodes early.

    Both arguments must either be timezone-aware or timezone-naive. RSS feed
    generation normalizes both values to Pacific time before calling this.
    """
    if (release_date.tzinfo is None) != (current_time.tzinfo is None):
        raise ValueError("release_date and current_time must have matching timezone awareness")

    current_occurrence = _date_in_year(release_date, current_time.year)
    if current_occurrence <= current_time:
        return current_occurrence

    return _date_in_year(release_date, current_time.year - 1)
