from flask import render_template
import jinja2
import ee
import pandas as pd

def get_dataset_for_polygon(is_polytrend, collection, AOI, scale, crs):
    crs = collection.first().getInfo()['bands'][0]['crs']
    print('crs', crs)
    geom_values = collection.getRegion(geometry=AOI, scale=scale, crs=crs)
    geom_values_list = ee.List(geom_values).getInfo()

    # Convert to a Pandas DataFrame.
    header = geom_values_list[0]
    data = pd.DataFrame(geom_values_list[1:], columns=header)
    if (is_polytrend): 
        data['datetime'] = pd.to_datetime(data['time'], unit='ms').dt.date
        data.set_index('datetime')
    else:
        data['time'] = [pd.to_datetime(item['value'], unit='ms') for item in data['time']]
        data.set_index('time')
    data.groupby(['longitude', 'latitude'])
    return data

def get_dataset_for_point(is_polytrend, collection, AOI, scale, crs):
    geom_values = collection.getRegion(geometry=AOI, scale=scale, crs=crs)
    geom_values_list = ee.List(geom_values).getInfo()
    header = geom_values_list[0]
    data = pd.DataFrame(geom_values_list[1:], columns=header)
    if (is_polytrend): 
        data['datetime'] = pd.to_datetime(data['time'], unit='ms', utc=True).dt.date
    else:
        data['time'] = [pd.to_datetime(item['value'], unit='ms') for item in data['time']]
    data.set_index('time')
    data.groupby(['longitude', 'latitude'])
    return data

def get_PT_statistics(result):
    result_to_display = {}
    linear = result.loc[result['trend_type'] == 1]
    no_trend = result.loc[result['trend_type'] == 0]
    concealed = result.loc[result['trend_type'] == -1]
    quadratic = result.loc[result['trend_type'] == 2]
    cubic = result.loc[result['trend_type'] == 3]
    negative = result.loc[result['direction'] == -1]
    positive = result.loc[result['direction'] == 1]

    result_to_display['count_total'] = len(result)
    result_to_display['count_linear'] = len(linear)
    result_to_display['count_no_trend'] = len(no_trend)
    result_to_display['count_concealed'] = len(concealed)
    result_to_display['count_quadratic'] = len(quadratic)
    result_to_display['count_cubic'] = len(cubic)
    result_to_display['count_negative'] = len(negative)
    result_to_display['count_positive'] = len(positive)

    count_total = result_to_display['count_total']
    result_to_display['proc_linear'] = round((result_to_display['count_linear']/count_total) * 100, 1)
    result_to_display['proc_no_trend'] = round((result_to_display['count_no_trend']/count_total) * 100, 1)
    result_to_display['proc_concealed'] = round((result_to_display['count_concealed']/count_total) * 100, 1)
    result_to_display['proc_quadratic'] = round((result_to_display['count_quadratic']/count_total) * 100, 1)
    result_to_display['proc_cubic'] = round((result_to_display['count_cubic']/count_total) * 100, 1)
    result_to_display['proc_negative'] = round((result_to_display['count_negative']/count_total) * 100, 1)
    result_to_display['proc_positive'] = round((result_to_display['count_positive']/count_total) * 100, 1)
    return result_to_display
