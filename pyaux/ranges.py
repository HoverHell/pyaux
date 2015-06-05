# coding: utf8
"""
Various range-generating funcs.
"""

__all__ = (
    'fxrange', 'frange', 'dxrange', 'drange',
    'date_xrange', 'date_range',
    'date_add_months', 'date_months_xrange', 'date_months_range',
)


def fxrange(start, end=None, inc=None):
    """ The xrange function for float """
    assert inc != 0, "inc should not be zero"
    if end is None:
        end = start
        start = 0.0
    if inc is None:
        inc = 1.0
    i = 0  # to prevent error accumulation
    while True:
        nextv = start + i * inc
        if (inc > 0 and nextv >= end or
                inc < 0 and nextv <= end):
            break
        yield nextv
        i += 1


def frange(start, end=None, inc=None):
    """ list(fxrange) """
    return list(fxrange(start, end, inc))


def dxrange(start, end=None, inc=None, include_end=False):
    """ The xrange function for Decimal """
    # Imported here mostly because of use_cdecimal in this module
    from decimal import Decimal
    assert inc != 0, "inc should not be zero"
    if end is None:
        end = start
        start = 0
    if inc is None:
        inc = 1
    inc = Decimal(inc)
    start = Decimal(start)
    end = Decimal(end)
    nextv = start
    while True:
        if ((inc > 0) and (not include_end and nextv == end or nextv > end) or
                (inc < 0) and (not include_end and nextv == end or nextv < end)):
            break
        yield nextv
        nextv += inc


def drange(*ar, **kwa):
    """ list(dxrange) """
    return list(dxrange(*ar, **kwa))


def date_xrange(start, end, inc=None, include_end=False, precise=False):
    """ The xrange function for datetime.

    NOTE: the semantics of 'start' and 'end' are different here: with
    end=None an infinite generator is returned.

    :param precise: do more calculations but potentially produce more
        precise results (especially for precise `inc`).

    >>> import datetime
    >>> dt = datetime.datetime
    >>> dta = dt(2011, 11, 11)
    >>> dtb = dt(2011, 11, 14)
    >>> dsl = lambda dtl: [dt.strftime('%Y-%m-%d') for dt in dtl]
    >>> dtsl = lambda dtl: [dt.isoformat() for dt in dtl]
    >>> dsl(date_xrange(dta, dt(2011, 11, 13)))
    ['2011-11-11', '2011-11-12']
    >>> dsl(date_xrange(dta, dt(2011, 11, 13), include_end=True))
    ['2011-11-11', '2011-11-12', '2011-11-13']
    >>> dsl(date_xrange(dta, dtb, inc=2))
    ['2011-11-11', '2011-11-13']
    >>> dtsl(date_xrange(dta, dtb, inc=1111.11111111111 / 86400, precise=True))[-1]
    '2011-11-13T23:54:48.888889'
    >>> dtsl(date_xrange(dta, dtb, inc=1111.11111111111 / 86400))[-1]
    '2011-11-13T23:54:48.888863'
    """
    import datetime
    if inc is None:
        inc = 1  # default: 1 day

    if not isinstance(inc, datetime.timedelta):
        # NOTE: days, by default
        inc_days = inc
        inc = datetime.timedelta(inc)
    else:
        inc_days = inc.total_seconds() / 86400  # py2.7 required

    assert inc_days  # should be nonzero

    is_forward = (inc_days > 0)

    idx = 0
    current = start
    while True:
        if end is not None:
            if include_end:
                to_break = current > end if is_forward else current < end
            else:
                to_break = current >= end if is_forward else current <= end
            if to_break:
                break
        yield current
        if precise:
            idx += 1
            current = start + datetime.timedelta(inc_days * idx)
        else:
            current = current + inc


def date_range(*ar, **kwa):
    """ list(date_xrange) """
    return list(date_xrange(*ar, **kwa))


def date_add_months(sourcedate, months=1):
    """ Add months to date; can cap the day to the maximal value for
    the month """
    import calendar
    month = sourcedate.month - 1 + months
    year = sourcedate.year + month // 12
    month = month % 12 + 1
    day = min(sourcedate.day, calendar.monthrange(year, month)[1])
    # return datetime.date(year, month, day)
    # On the other hand, we can keep the type and the time:
    return sourcedate.replace(year=year, month=month, day=day)


def date_months_xrange(start, end, inc=1, include_end=False):
    """ date_range with delta measured in months.

    Similar semantics to date_xrange.
    Only accepts integer `inc` values.

    >>> import datetime
    >>> dt = datetime.datetime
    >>> dsl = lambda dtl: [dt.strftime('%Y-%m-%d') for dt in dtl]
    >>> dsl(date_months_xrange(dt(2011, 10, 31), dt(2012, 1, 1)))
    ['2011-10-31', '2011-11-30', '2011-12-31']
    """
    assert isinstance(inc, int)
    inc = int(inc)
    assert inc  # should be nonzero
    is_forward = inc > 0
    current = start
    idx = 0
    while True:
        if end is not None:
            if include_end:
                to_break = current > end if is_forward else current < end
            else:
                to_break = current >= end if is_forward else current <= end
            if to_break:
                break
        yield current
        idx += 1
        current = date_add_months(start, months=inc * idx)


def date_months_range(*ar, **kwa):
    """ list(date_months_xrange) """
    return list(date_months_xrange(*ar, **kwa))
