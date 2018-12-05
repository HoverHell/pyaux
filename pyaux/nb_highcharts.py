# coding: utf8
"""
Helpers for using Highcharts / Highstock in an IPython notebook.
"""

import copy
import json
import random
import string
import time
import datetime
from IPython.display import HTML
from pyaux.base import dict_merge, group


def mk_uid():
    return ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(15))


def Highcharts_old(
        chart_def=None, chart_def_json=None, height=400, min_width=400, uid=None,
        highstock=True):
    assert chart_def or chart_def_json
    unique_id = mk_uid() if uid is None else uid
    chart_def_json = json.dumps(chart_def) if chart_def_json is None else chart_def_json
    if highstock:
        hsscript = "http://code.highcharts.com/stock/highstock.js"
    else:
        hsscript = "http://code.highcharts.com/highcharts.js"
    context = dict(
        chart_def_json=chart_def_json, chart_def=chart_def,
        min_width=min_width, height=height,
        unique_id=unique_id, hsscript=hsscript,
        hstag="'StockChart', " if highstock else "",
    )
    html = '''
    <script src="%(hsscript)s"></script>
    <script src="http://code.highcharts.com/modules/exporting.src.js"></script>

    <div id="chart_%(unique_id)s" style="min-width: %(min_width)spx; height: %(height)ipx; margin: 0 auto">Re-run cell if chart is not shown ...</div>
    <script>
        do_chart_%(unique_id)s = function() {
            $('#chart_%(unique_id)s').highcharts(%(hstag)s%(chart_def_json)s);
        }
        setTimeout("do_chart_%(unique_id)s()", 50)
    </script>
    ''' % context
    res = HTML(html)
    res.context = context
    return res




def RunJS(js, delayed=50):
    context = dict(js=js, unique_id=mk_uid(), delayed=delayed)
    if not delayed:
        html = '''
        <script>
        %(js)s
        </script>
        ''' % context
    else:
        html = '''
        <script>
            tmp_run_%(unique_id)s = function() {
                %(js)s
            }
            setTimeout("tmp_run_%(unique_id)s()", %(delayed)d)
        </script>
        ''' % context
    return HTML(html)


def Highcharts(
        chart_def=None,
        width=1800,
        height=800,
        highstock=True,
        **kwargs):
    if highstock:
        from highcharts import Highstock
        chart = Highstock()
    else:
        from highcharts import Highchart
        chart = Highchart()
    chart_def = chart_def.copy()
    chart_def['chart'] = (chart_def.get('chart') or {}).copy()
    chart_def['chart']['width'] = width
    chart_def['chart']['height'] = height

    series = chart_def.pop('series')
    chart.set_dict_options(chart_def)

    for line in series:
        chart.add_data_set(**line)

    # Note: this one essentially uses an iframe (in jupyter).
    return chart


def mk_chart_def(
        df=None,
        kwa=None,
        series=None,
        chart_type='line',
        timestamp_in_idx='auto',
        margin_right=130,
        margin_bottom=25,
        title='',
        subtitle='',
        xlabel='',
        ylabel='',
        zip_idx=True):
    """
    Convert a Pandas dataframe (or something else) to a highcharts
    chart definition.

    Sample serie: `dict(name='serie_name', data=[1.1, 2.2, 3.3])`.
    """
    series = [] if series is None else copy.copy(series)
    res = dict(
        chart={},
        title={},
        subtitle={},
        xAxis={},
        yAxis={},
        tooltip={},
        legend=dict(
            layout='vertical',
            align='right',
            verticalAlign='top',
            x=-10,
            y=100,
            borderWidth=0,
        ),
        plotOptions=dict(
            series=dict(
                animation=False,
                marker=dict(
                    enabled=True,
                ),
            ),
        ),
        series=series,
    )
    if chart_type is not None:
        res['chart']['type'] = chart_type
    if margin_right is not None:
        res['chart']['marginRight'] = margin_right
    if margin_bottom is not None:
        res['chart']['marginBottom'] = margin_bottom
    if title:
        res['title'].update(
            text=title,
            # center, supposedly
            x=-20)
    if subtitle:
        res['subtitle'].update(
            text=subtitle,
            x=-20)
    if xlabel:
        res['xAxis']['title'] = dict(text=xlabel)
    if ylabel:
        res['yAxis']['title'] = dict(text=ylabel)

    if df is not None:
        idx = df.index

        if timestamp_in_idx == 'auto':
            timestamp_in_idx = isinstance(idx[0], datetime.date)

        if timestamp_in_idx:
            res['xAxis']['type'] = 'datetime'

        df = df.applymap(lambda val: dt_to_hc(val) if isinstance(val, (datetime.date, datetime.datetime)) else val)
        if timestamp_in_idx:
            idx = [dt_to_hc(val) for val in idx]
            zip_idx = True

        if zip_idx:
            series.extend(
                dict(name=column, data=zip(idx, list(df[column])))
                for column in df.columns)
        else:
            series.extend(
                dict(name=column, data=list(df[column]))
                for column in df.columns)

    if kwa:
        res = dict_merge(res, kwa, _copy=False)

    return res


def dt_to_hc(dt):
    """ datetime -> highcharts value """
    return int(time.mktime(dt.timetuple()) * 1e3 + dt.microsecond / 1e3)


def ohlc_to_data(df, cols='o h l c'.split(), **kwa):
    """ OHLC dataframe -> data """
    res = [
        ([dt_to_hc(idx.to_datetime())] +
         [row[col] for col in cols])
        for idx, row in df.iterrows()]
    return res


def ohlc_to_serie(df, name=None, extra=None, grouping_units=None, **kwa):
    """ Helper to convert OHLC data to highcharts series """
    if grouping_units is None:
        grouping_units = [
            # unit name, [allowed multiples],
            ['week', [1]],
            ['month', [1, 2, 3, 4, 6]],
        ]
    res_candle = dict(
        type='candlestick',
        name=name,
        # sample data: [[1367366400000,444.46,444.93,434.39,439.29], …]
        data=ohlc_to_data(df, **kwa),
        dataGrouping=dict(units=grouping_units))
    if extra:
        res_candle = dict_merge(res_candle, extra, _copy=False)
    return res_candle


def interleave(joiner, iterable):
    """
    Similar to `str.join` but for lists.

    >>> interleave([1], [2, 3, 4])
    [2, 1, 3, 1, 4]
    """
    try:
        yield next(iterable)
    except StopIteration:  # empty
        return
    for item in iterable:
        yield joiner
        yield item


def ohlcv_to_cdef(df, name, volume='v', pois=None, poi_to_color='default', **kwa):
    """ Helper to convert OHLCV data to a chart def.

    `pois`: [
        # poi
        [
            # point
            [idx, value],
            # point
            [... second point ...]],
        ... more poi ...]
    """
    candle_serie = ohlc_to_serie(df, name, **kwa)
    series = [candle_serie]
    extras = {}
    if volume and volume in df:
        volume_series = df[volume]
        volume_data = [[dt_to_hc(idx.to_datetime()), val]
                       for idx, val in volume_series.iteritems()]
        series.append(dict(
            type='column', name='Volume', data=volume_data,
            yAxis=1,  # Need an axis for that
            dataGrouping=candle_serie['dataGrouping']))
        extras.update(yAxis=[
            dict(labels=dict(align='right', x=-3),
                 title=dict(text='OHLC'),
                 height='60%', lineWidth=2),
            dict(labels=dict(align='right', x=-3),
                 title=dict(text='Volume'),
                 top='65%', height='35%',
                 offset=0, lineWidth=2),
            ])
    if pois:
        breakpointer = [None, None]

        def poi_to_color_default(poi):
            # red if downwards else green
            return 'red' if poi[1][1] < poi[0][1] else 'green'

        if poi_to_color == 'default':
            poi_to_color = poi_to_color_default
        poi_grouped = group((poi_to_color(poi), poi) for poi in pois)
        for color, poi_group in poi_grouped.items():
            poi_data = [
                (dt_to_hc(point_ts) if point_ts else None,
                 point_val)
                for poi in interleave([breakpointer], poi_group)
                for point_ts, point_val in poi]
            series.append(dict(
                type='line', name='POI', data=poi_data,
                color=color,
                # dataGrouping=candle_serie['dataGrouping']
            ))

    return mk_chart_def(series=series, kwa=extras)
