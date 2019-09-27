from flask import Flask, render_template, url_for, request, flash, Blueprint     
import jinja2
#for transforming R objects
from rpy2.robjects.packages import importr
from rpy2.robjects.vectors import FloatVector
import rpy2.robjects as ro
import re
import numpy as np
import pandas as pd
import geopandas as gpd 
import pandas_bokeh
from shapely.geometry import Point
# for bokeh maps and plots
from bokeh.io import show
from bokeh.models import LinearColorMapper, ColorBar
from bokeh.palettes import Viridis256 as palette
from bokeh.plotting import figure, ColumnDataSource
from bokeh.layouts import layout, row
from bokeh.embed import components
#local import
from TrendEngine.main.forms import DbestParametersForm
from .utils import get_dataset_for_point, get_dataset_for_polygon

try:
    import ee
except ImportError:
    raise ImportError(
        "You either haven't installed or authenticated Earth Engine"
        )
ee.Initialize()

def calculate_dbest_for_polygon(dataset, data_type, seasonality, algorithm, breakpoints_no, 
            first_level_shift, second_level_shift, duration, distance_threshold, 
            alpha, n, number_of_pixels):
    """ For polygons splits the image into pixels and runs DBEST
        separately on each pixel time series list of values
        For pixels runs the DBEST package on time series list
    """
    DBEST_result = []
    if (data_type == 'non-cyclical'):
        pass
        
    elif (data_type == 'cyclical'):
        DBEST_result_header = ['geometry', 'start', 'duration', 'end', 'change', 'change_type', 'significance']
        for i in range(0, number_of_pixels, n):
            Y_long = dataset[i:i+n][band_name].values 
            Y = [round(x, 3) for x in Y_long]
            if (all(val > ndvi_threshold for val in Y)):
                vec =  FloatVector(Y)
                try:
                    result = list(dbest.DBEST(
                        data=vec, 
                        data_type=data_type, 
                        seasonality=seasonality, 
                        algorithm=algorithm, 
                        breakpoints_no=breakpoints_no, 
                        first_level_shift=first_level_shift, 
                        second_level_shift=second_level_shift, 
                        duration=duration, 
                        distance_threshold=distance_threshold, 
                        alpha=alpha
                        ))
                    #populate the empty PT_result list with values    
                    pixel_long = dataset.at[i, 'longitude']
                    pixel_lat = dataset.at[i, 'latitude']
                    geometry = [round(pixel_long, 4), round(pixel_lat, 4)]
                    DBEST_result.append([geometry, int(result[2][0]), int(result[3][0]), int(result[4][0]), 
                        float(result[5][0]), int(result[6][0]), result[7][0]]) 
                except:
                    return render_template('error.html')
                    print('Error comes from R')    
            else:
                print('!!!!!!!!!!!!!!! Unqualified value !!!!!!!!!!!!!!!!!!!!!!!!!!!!')
                                
        df = pd.DataFrame(DBEST_result[0:], columns=DBEST_result_header)
        if df.empty:
            print('!!!!!!!!!!!!!! Too many unqualified values !!!!!!!!!!!!!!')
            exit()
    return df

def calculate_dbest_for_point(dataset, data_type, seasonality, algorithm, breakpoints_no, first_level_shift, 
            second_level_shift, duration, distance_threshold,alpha):
    # get only NDVI values for pixel
    Y = dataset[band_name].values
    print(Y)
    if (all(val > ndvi_threshold for val in Y)): 
        vec =  FloatVector(Y)
        ro.globalenv["dbest_result"] = dbest.DBEST(
            data=vec, data_type=data_type, 
            seasonality=seasonality, 
            algorithm=algorithm, 
            breakpoints_no=breakpoints_no, 
            first_level_shift=first_level_shift, 
            second_level_shift=second_level_shift, 
            duration=duration, 
            distance_threshold=distance_threshold, 
            alpha=alpha
            )
        dbest_result = list(ro.r('dbest_result'))
        df = pd.DataFrame(dbest_result)
    else:
        print('!!!!!!!!!!!!!!!!! Values below threshold !!!!!!!!!!!!!!!!!!!!!')
        exit()
    return df

def dbest_visualize_polygon(result, algorithm):
    """ Create maps for polygons

    Args:
        result: dataframe
            contains what comes out of DBEST package 
        algorithm: string
            'generalization' or 'change detection' depending on user's choice

    Returns: 
        render_template with graphics

    """
    result_to_display = {}
    if (data_type == 'cyclical'):
        gpd_coordinates = result['geometry'].apply(Point)
        gpd_df = gpd.GeoDataFrame(result, geometry = gpd_coordinates)
        gpd_df.crs = {'init' :'epsg:4326'}
        pointA = result["geometry"][0]
        pointB = result["geometry"][1]
        print(' pt A', pointA)
        print('pt B ', pointB)
        buffer_size = pointA.distance(pointB)/2
        print('buffer is ', buffer_size)
        print('pointA is ', pointA)
        gpd_df.geometry = gpd_df.geometry.buffer(buffer_size).envelope
        mapper = LinearColorMapper(palette=palette)
        colormap = ['grey', 'yellow']
        start_map = gpd_df.plot_bokeh(
            category='start', 
            colormap=palette, 
            title='Start time',
            legend='Start time', 
            line_color=None,
            show_figure=False, 
            show_colorbar=True)

        duration_map = gpd_df.plot_bokeh(
            category='duration', 
            colormap=palette, 
            title='Duration (months)', 
            legend='Duration', 
            line_color=None, 
            show_figure=False)

        change_map = gpd_df.plot_bokeh(
            category='change', 
            colormap=palette, 
            title='Change map', 
            legend='Change value', 
            line_color=None, 
            show_figure=False)

        change_type_map = gpd_df.plot_bokeh(
            category='change_type', 
            colormap=colormap, 
            title='Change type map - abrupt (1), non-abrupt (0)', 
            legend='Change type', 
            line_color=None, 
            # return_html=True, 
            show_figure=False)

        plot_grid = pandas_bokeh.plot_grid(
            [[change_map, duration_map],[start_map, change_type_map]], 
            return_html=True, show_plot=False)
        script = ''
        div = ''
        generalization = ''
        change_detection = ''
    elif (data_type == 'non-cyclical'):
        plot_grid = ''
        script = ''
        div = ''
        generalization = 'No result for non-cyclical data yet...'
        change_detection = ''
    
    return render_template(
        "results_DBEST.html", 
        generalization=generalization,
        change_detection = change_detection,
        dbest_maps=plot_grid, 
        result=result_to_display, 
        is_point=is_point, 
        script=script, 
        div=div)

def dbest_visualize_point(result, time_steps, algorithm):
    """ Create plots for points depending on the algorithm passed:
        for 'generalization': generalized trend and f-local-change
        for 'change detection': data, trend, seasonal, remainder

    Args:
        result: Pandas dataframe
            contains what comes out of DBEST package 
        time_steps: list
            list of dates for time series representation
        algorithm: string
            'generalization' or 'change detection' depending on user's choice

    Returns: 
        render_template with graphics

    """

    if (algorithm == 'change detection'):
        start_arr= np.asarray(result[0][2])
        # Create a dictionary for textual output in result_DBEST.html
        result_to_display = {
        'breakpoint_no': np.asarray(result[0][0]),
        'segment_no': np.asarray(result[0][1]),
        'start': start_arr,
        'first_change': time_steps[start_arr[0]],
        'duration': np.asarray(result[0][3]),
        'end': np.asarray(result[0][4]),
        'change': np.asarray(result[0][5]),
        'change_type': np.asarray(result[0][6]),
        'significance': np.asarray(result[0][7])
        }
        # Create plots 
        fit = np.ravel(result[0][8])
        data = np.asarray(result[0][9])
        trend = np.asarray(result[0][10])
        seasonal = np.asarray(result[0][11])
        remainder = np.asarray(result[0][12])
        start = np.asarray(result[0][2])
        end_float = np.asarray(result[0][4])
        end = [int(item) for item in end_float]

        data_plot  = figure(
            background_fill_color='lightgrey', 
            height=400, 
            width=700, 
            x_axis_type="datetime", 
            toolbar_location=None)
        data_plot.title.text = 'Data'
        data_plot.line(x=time_steps, y=data)

        trend_plot = figure(
            background_fill_color='lightgrey', 
            height=400, 
            width=700, 
            x_axis_type="datetime", 
            toolbar_location=None)
        trend_plot.title.text = 'Trend'
        trend_plot.line(x=time_steps, y=trend)

        seasonal_plot = figure(
            background_fill_color='lightgrey', 
            height=400, 
            width=700, 
            x_axis_type="datetime", 
            toolbar_location=None)
        seasonal_plot.title.text = 'Seasonal'
        seasonal_plot.line(x=time_steps, y=seasonal)

        remainder_plot = figure(
            background_fill_color='lightgrey', 
            height=400, 
            width=700, 
            x_axis_type="datetime", 
            toolbar_location=None)
        source = ColumnDataSource(
            data=dict(
                x0 = time_steps, 
                y0 = [0]*len(time_steps), 
                x1 = time_steps, 
                y1 = remainder
            ))
        remainder_plot.title.text = 'Remainder'
        remainder_plot.segment(
            x0='x0', 
            y0='y0', 
            x1='x1', 
            y1= 'y1', 
            source=source)
        grid = layout(
            [[data_plot, trend_plot], 
            [seasonal_plot, remainder_plot]],
            sizing_mode="scale_both")
        generalization = False
        change_detection = True

    if (algorithm == 'generalization'):
        # Create a dictionary for textual output in result_DBEST.html
        result_to_display = {
            'segment_no': np.asarray(result[0][0]),
            'RMSE': np.asarray(result[0][1]),
            'MAD': np.asarray(result[0][2])
        }
        # Create plots
        f_local = np.asarray(result[0][8])
        fit = np.ravel(result[0][3])
        data = np.asarray(result[0][4])
        print('!!!! result ', result[0])
        fit_plot = figure(
            background_fill_color="lightgrey", 
            height=400, 
            width=700, 
            x_axis_type = "datetime", 
            toolbar_location = None)
        fit_plot.title.text = 'Generalized trend'
        fit_plot.line(x=time_steps, y=data, color='blue')
        fit_plot.line(x=time_steps, y=fit, color='green', line_width=2)

        f_local_plot = figure(
            background_fill_color='lightgrey', 
            height=400, 
            width=700, 
            x_axis_type = "datetime", 
            toolbar_location=None)
        source = ColumnDataSource(
            data=dict(
                x0 = time_steps, 
                y0 = [0]*len(time_steps), 
                x1 = time_steps, 
                y1 = f_local
            ))
        f_local_plot.title.text = 'Trend local change'
        f_local_plot.segment(
            x0='x0', 
            y0='y0', 
            x1='x1', 
            y1= 'y1', 
            source=source, 
            color='red')
        grid = layout([fit_plot, f_local_plot])
        generalization = True
        change_detection = False

    script, div = components(grid)
    plot_grid = ''

    return render_template(
        "results_DBEST.html", 
        generalization=generalization,
        change_detection = change_detection,
        dbest_maps=plot_grid, 
        result=result_to_display, 
        is_point=is_point, 
        script=script, 
        div=div)


def dbest_func(parameters):
    """ Get data from GEE, split images into pixel time series,
        call DBEST R package for a list of time series values
        for each pixel separately

        Called from .routes.py

    Args:
        parameters: dict
            contains all parameters entered by the user to query data 
            and parameters for the DBEST algorithm

    Returns: 
        render template result_DBEST.html with maps for polygon or plots for point

    """
    #getting data parameters
    name_of_collection = parameters['dataset_name']
    if (name_of_collection == 'NASA/GIMMS/3GV0'):
        band_name = 'ndvi'
        scale = 8000
        ndvi_threshold = 0.1
    elif (name_of_collection == 'MODIS/006/MOD13Q1_NDVI'):
        name_of_collection = 'MODIS/006/MOD13Q1'
        band_name = 'NDVI'
        scale = 250
        ndvi_threshold = 100
    elif (name_of_collection == 'MODIS/006/MOD13Q1_EVI'):
        name_of_collection = 'MODIS/006/MOD13Q1'
        band_name = 'EVI'
        scale = 250
        ndvi_threshold = 100
    coordinates = parameters['coordinates']
    regex = re.sub("[\[\]]", "", coordinates)
    split = regex.split(',')
    coords = list(map(float, split))
    if (len(coords) > 2):
        aoi = ee.Geometry.Polygon(coords)
        is_polygon = True
        is_point = False
    elif (len(coords) == 2):
        aoi = ee.Geometry.Point(coords)
        is_point = True
        is_polygon = False
    else:
        print('wrong coordinates')
    start_date = parameters['date_from']
    end_date = parameters['date_to']
    start_year = int(start_date.split('-')[0])
    end_year = int(end_date.split('-')[0])
    img_collection = ee.ImageCollection(name_of_collection) 
    crs = img_collection.first().getInfo()['bands'][0]['crs']
    collection = img_collection.filterDate(start_date, end_date).filterBounds(aoi)
    save_ts_to_csv = parameters['save_ts_to_csv']
    save_result_to_csv = parameters['save_result_to_csv']
    is_polytrend = False 
    # end of getting data parameters

    #getting algorithm parameters for DBEST
    data_type = parameters['data_type']
    seasonality = int(parameters['seasonality'])
    algorithm = parameters['algorithm']
    breakpoints_no = int(parameters['breakpoint_no'])
    first_level_shift = float(parameters['first_level_shift'])
    second_level_shift = float(parameters['second_level_shift'])
    duration = int(parameters['duration'])
    distance_threshold = parameters['distance']
    if distance_threshold != 'default':
        distance_threshold = float(distance_threshold)
    alpha = float(parameters['alpha'])
    #end of getting DBEST parameters

    if (is_polygon):

        years = ee.List.sequence(start_year, end_year, 1)

        def calculate_monthly_mean_for_years(year_and_collection):
          # Unpack variable from the input parameter
            year_and_collection = ee.List(year_and_collection)
            year = ee.Number(year_and_collection.get(0))
            _collection = ee.ImageCollection(year_and_collection.get(1))
            start_date = ee.Date.fromYMD(year, 1, 1)
            end_date = start_date.advance(1, 'year')
            annual = _collection.filterDate(start_date, end_date)
            
            months =ee.List.sequence(1, 12, 1)
            def get_monthly(month_and_collection):
                month_and_collection = ee.List(month_and_collection)
                month = ee.Number(month_and_collection.get(0))
                _collection = ee.ImageCollection(month_and_collection.get(1))
                start_date = ee.Date.fromYMD(year, month, 1)
                end_date = start_date.advance(1, 'month')
                monthly_coll = _collection.filterDate(start_date, end_date).mean().set('system:time_start', start_date)
                return monthly_coll
            
            list_of_months_and_collections = months.zip(ee.List.repeat(annual, months.length()))
            monthly_NDVI_collection = list_of_months_and_collections.map(get_monthly)
            return monthly_NDVI_collection

        # Create a list of year-collection pairs (i.e. pack the function inputs)
        list_of_years_and_collections = years.zip(ee.List.repeat(collection, years.length()))

        monthly_NDVI_list = list_of_years_and_collections.map(calculate_monthly_mean_for_years).flatten()
        monthly_NDVI = ee.ImageCollection.fromImages(monthly_NDVI_list)
        dataset = get_dataset_for_polygon(is_polytrend, monthly_NDVI, aoi, scale, crs)
        number_of_pixels = len(dataset) 
        print(number_of_pixels)
        list_of_images = dataset['id']
        ids_of_images = []
        for img_id in list_of_images:
            if img_id not in ids_of_images:
                ids_of_images.append(img_id)
        n = len(ids_of_images)
        if (save_ts_to_csv):
            dataset.to_csv('time_series.csv')

        dbest = importr('DBEST', robject_translations = {
            "data.type": "data_type", 
            "breakpoints.no": "breakpoints_no", 
            "first.level.shift": "first_level_shift", 
            "second.level.shift":"second_level_shift", 
            "distance.threshold": "distance_threshold"
            })

        result = calculate_dbest_for_polygon(dataset, data_type, seasonality, algorithm, breakpoints_no, 
            first_level_shift, second_level_shift, duration, distance_threshold, alpha, n, number_of_pixels)
        if (save_result_to_csv):
            result.to_csv('DBEST_result.csv')
        plot = dbest_visualize_polygon(result, algorithm)

    elif (is_point):

        years = ee.List.sequence(start_year, end_year, 1)
        MOD13Q1 = collection.filterBounds(aoi).filterDate(start_date, end_date).select(band_name)

        def calculate_monthly_mean_for_years(year_and_collection):
          # Unpack variable from the input parameter
            year_and_collection = ee.List(year_and_collection)
            year = ee.Number(year_and_collection.get(0))
            _collection = ee.ImageCollection(year_and_collection.get(1))
            start_date = ee.Date.fromYMD(year, 1, 1)
            end_date = start_date.advance(1, 'year')
            annual = _collection.filterDate(start_date, end_date)
            
            months =ee.List.sequence(1, 12, 1)
            def get_monthly(month_and_collection):
                month_and_collection = ee.List(month_and_collection)
                month = ee.Number(month_and_collection.get(0))
                _collection = ee.ImageCollection(month_and_collection.get(1))
                start_date = ee.Date.fromYMD(year, month, 1)
                end_date = start_date.advance(1, 'month')
                monthly_coll = _collection.filterDate(start_date, end_date).mean().set('system:time_start', start_date)
                return monthly_coll
            
            list_of_months_and_collections = months.zip(ee.List.repeat(annual, months.length()))
            monthly_NDVI_collection = list_of_months_and_collections.map(get_monthly)
            return monthly_NDVI_collection

        # Create a list of year-collection pairs (i.e. pack the function inputs)
        list_of_years_and_collections = years.zip(ee.List.repeat(MOD13Q1, years.length()))

        monthly_NDVI_list = list_of_years_and_collections.map(calculate_monthly_mean_for_years).flatten()
        monthly_NDVI = ee.ImageCollection.fromImages(monthly_NDVI_list)
        print('size of annual',monthly_NDVI.size().getInfo())
        dataset = get_dataset_for_polygon(is_polytrend, monthly_NDVI, aoi, scale, crs)
        number_of_pixels = len(dataset) 
        print(number_of_pixels)
        
        dbest = importr('DBEST', robject_translations = {
            "data.type": "data_type", 
            "breakpoints.no": "breakpoints_no", 
            "first.level.shift": "first_level_shift", 
            "second.level.shift":"second_level_shift", 
            "distance.threshold": "distance_threshold"
            })

        time_steps = dataset['time']
        result = calculate_dbest_for_polygon(dataset, data_type, seasonality, algorithm, 
            breakpoints_no, first_level_shift, second_level_shift, duration, 
            distance_threshold,alpha)
        if (save_result_to_csv):
            result.to_csv('DBEST_result.csv')
        plots = dbest_visualize_point(result, time_steps, algorithm)

    return plots




