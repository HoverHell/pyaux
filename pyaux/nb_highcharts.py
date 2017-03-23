# coding: utf8
"""
Helpers for using Highcharts / Highstock in an IPython notebook.
"""

import copy
import json
import random
import string
import time
from IPython.display import HTML
from pyaux.base import dict_merge, group


def mk_uid():
    return ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for _ in range(15))


def Highcharts(
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
    <script src="http://code.highcharts.com/modules/exporting.js"></script>

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


def RunJS(js):
    context = dict(js=js, unique_id=mk_uid())
    html = '''
    <script>
    %(js)s
    </script>
    ''' % context
    html_v2 = '''
    <script>
      <script>
        tmp_run_%(unique_id)s = function() {
            %(js)s
        }
        setTimeout("tmp_run_%(unique_id)s()", 50)
    </script>
    ''' % context
    # TODO: test which one works better
    return HTML(html)


def mk_chart_def(
        df=None, kwa=None, series=None, chart_type='line',
        timestamp_in_idx=False,
        marginRight=130, marginBottom=25, title='', subtitle='',
        xlabel='', ylabel=''):
    """
    Convert a Pandas dataframe (or something else) to a highcharts
    chart definition.

    Sample serie: `dict(name='serie_name', data=[1.1, 2.2, 3.3])`.
    """
    series = [] if series is None else copy.copy(series)
    res = dict(
        chart=dict(
            type=chart_type, marginRight=marginRight,
            marginBottom=marginBottom),
        title=dict(
            text=title,
            # center, supposedly
            x=-20),
        subtitle=dict(
            text=subtitle,
            x=-20),
        xAxis=dict(title=dict(text=xlabel)),
        yAxis=dict(
            title=dict(text=ylabel),
            # plotLines=[dict(value=0, width=1, color='#808080')],
        ),
        tooltip=dict(
            # valueSuffix=u'°C',
        ),
        legend=dict(
            layout='vertical',
            align='right', verticalAlign='top',
            x=-10, y=100, borderWidth=0,
        ),
        series=series,
    )

    if df is not None:
        if timestamp_in_idx:
            idx = [dt_to_hc(val.to_datetime()) for val in df.index]
            series.extend(
                dict(name=column, data=zip(idx, list(df[column])))
                for column in df.columns)
        else:
            series.extend(
                dict(name=column, data=list(df[column]))
                for column in df.columns)

    if kwa:
        from pyaux.base import dict_merge
        res = dict_merge(res, kwa, _copy=False)

    return res


def dt_to_hc(dt):
    """ datetime -> highcharts value """
    return int(time.mktime(dt.timetuple()) * 1e3)


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
        grouping_units=[
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
        from pyaux.base import dict_merge
        res_candle = dict_merge(res_candle, extra, _copy=False)
    return res_candle


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
        breakpoint = [None, None]

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
                for poi in interleave([breakpoint], poi_group)
                for point_ts, point_val in poi]
            series.append(dict(
                type='line', name='POI', data=poi_data,
                color=color,
                # dataGrouping=candle_serie['dataGrouping']
            ))

    return mk_chart_def(series=series, kwa=extras)
