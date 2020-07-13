from flask import Flask, render_template, url_for, request, flash, Blueprint
import jinja2
from werkzeug import ImmutableMultiDict

# for pie charts
from math import pi
from bokeh.transform import cumsum

# for transforming R objects
import numpy as np
import pandas as pd
import geopandas as gpd
import pandas_bokeh
from shapely.geometry import Point
from rpy2.robjects.packages import importr
from rpy2.robjects.vectors import FloatVector
import rpy2.robjects as ro
import re

# for bokeh maps and plots
from bokeh.io import show
from bokeh.models import LinearColorMapper, ColorBar
from bokeh.palettes import Viridis256 as palette
from bokeh.plotting import figure, ColumnDataSource
from bokeh.layouts import layout, row
from bokeh.embed import components

# local imports
from .polytrend_pkg import PolyTrend
from .utils import get_dataset_for_point, get_dataset_for_polygon, get_PT_statistics

try:
    import ee
except ImportError:
    raise ImportError("You either haven't installed or authenticated Earth Engine")
ee.Initialize()


def visualize_polytrend_polygon(result):
    """ Create maps for polygons

    Args:
        result: list 
            contains what comes out of PolyTrend R package 

    Returns: 
        render_template with graphics

    """
    ## get staticstics for all points
    result_to_display = get_PT_statistics(result)
    trend_stats = {
        "concealed": result_to_display["count_concealed"],
        "linear": result_to_display["count_linear"],
        "no trend": result_to_display["count_no_trend"],
        "quadratic": result_to_display["count_quadratic"],
        "cubic": result_to_display["count_cubic"],
    }
    # get pie plots for summary statistics
    trend_data = (
        pd.Series(trend_stats)
        .reset_index(name="value")
        .rename(columns={"index": "trend"})
    )
    trend_data["angle"] = trend_data["value"] / trend_data["value"].sum() * 2 * pi
    trend_data["color"] = ["gray", "forestgreen", "yellow", "blue", "red"]
    trend_pie = figure(
        plot_height=350,
        title="Trend type (share in total number of pixels)",
        toolbar_location=None,
        tools="hover",
        tooltips="@trend: @value",
        x_range=(-0.5, 1.0),
        sizing_mode="scale_both",
    )
    trend_pie.wedge(
        x=0,
        y=1,
        radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend="trend",
        source=trend_data,
    )

    trend_pie.axis.axis_label = None
    trend_pie.axis.visible = False
    trend_pie.grid.grid_line_color = None

    direction_stats = {
        "negative": result_to_display["count_negative"],
        "positive": result_to_display["count_positive"],
    }
    dir_data = (
        pd.Series(direction_stats)
        .reset_index(name="value")
        .rename(columns={"index": "direction"})
    )
    dir_data["angle"] = dir_data["value"] / dir_data["value"].sum() * 2 * pi
    dir_data["color"] = ["gray", "forestgreen"]
    direction_pie = figure(
        plot_height=350,
        title="Change direction (share in total number of pixels)",
        toolbar_location=None,
        tools="hover",
        x_range=(-0.5, 1.0),
        sizing_mode="scale_both",
        tooltips="@direction: @value",
    )
    direction_pie.wedge(
        x=0,
        y=1,
        radius=0.4,
        start_angle=cumsum("angle", include_zero=True),
        end_angle=cumsum("angle"),
        line_color="white",
        fill_color="color",
        legend="direction",
        source=dir_data,
    )
    direction_pie.axis.axis_label = None
    direction_pie.axis.visible = False
    direction_pie.grid.grid_line_color = None
    pie_layout = row([trend_pie, direction_pie], sizing_mode="stretch_both")
    script, div = components(pie_layout)

    ### get maps
    gpd_coordinates = result["geometry"].apply(Point)
    gpd_df = gpd.GeoDataFrame(result, geometry=gpd_coordinates)
    gpd_df.crs = {"init": "epsg:4326"}
    pointA = result["geometry"][0]
    pointB = result["geometry"][1]
    buffer_size = pointA.distance(pointB) / 2
    gpd_df.geometry = gpd_df.geometry.buffer(buffer_size).envelope
    colormap_trend = ["grey", "yellow", "green", "blue", "red"]
    trend_map = gpd_df.plot_bokeh(
        category="trend_type",
        colormap=colormap_trend,
        line_color=None,
        title="Map of trend types",
        legend="Trend type",
        show_figure=False,
        show_colorbar=True,
        hovertool_columns="all",
    )

    colormap_dir = ["yellow", "green"]
    direction_map = gpd_df.plot_bokeh(
        category="direction",
        colormap=colormap_dir,
        line_color=None,
        title="Map of direction",
        legend="Direction",
        show_figure=False,
        show_colorbar=True,
        hovertool_columns="all",
    )
    slope_map = gpd_df.plot_bokeh(
        category="slope",
        fill_color=palette,
        legend="Slope",
        title="Slope map",
        show_figure=False,
        line_color=None,
        hovertool_columns="all",
    )
    plot_grid = pandas_bokeh.plot_grid(
        [[trend_map, direction_map], [slope_map]], show_plot=False, return_html=True
    )
    return render_template(
        "results_polytrend.html",
        result=result_to_display,
        pt_map=plot_grid,
        script=script,
        div=div,
        is_point=False,
    )


def visualize_polytrend_point(result, name_of_collection, start_year):
    """ Create a time series plot with regression line fitted

    Args:
        result: list 
            contains what comes out of PolyTrend R package 
        name_of_collection: string
            ID of dataset in Google Earth Engine entered by user the form in home.html
        start_year: int
            year from which image collection starts

    Returns: 
        render_template with graphics

    """
    #### create a plot for a point ####
    if name_of_collection == "NASA/GIMMS/3GV0":
        y_axis_range = (0, 1)
    else:
        y_axis_range = (-2000, 10000)
    degree = int(result["degree"][0])
    trend_type_index = int(result["trend_type"][0])
    direction_index = int(result["direction"][0])
    trend_type_dict = {
        -1: "concealed",
        0: "no trend",
        1: "linear",
        2: "cuadratic",
        3: "cubic",
    }
    direction_dict = {-1: "negative", 1: "positive"}
    result_to_display = {
        "slope": round(result["slope"][0], 2),
        "trend": trend_type_dict[trend_type_index],
        "direction": direction_dict[direction_index],
        "significance": result["significance"][0],
    }

    y = result["ts"][0]
    no_of_years_valid = len(y)
    end_year = start_year + no_of_years_valid
    x = range(start_year, end_year)

    coefficients = np.polyfit(x, y, degree)
    t = np.linspace(start_year, end_year)
    regression = np.poly1d(coefficients)
    # define what goes on the plot
    trend_plot = figure(
        plot_width=600,
        plot_height=300,
        x_axis_type="linear",
        y_range=y_axis_range,
        toolbar_location=None,
    )
    trend_plot.line(x, y, color="navy", alpha=0.5)
    trend_plot.circle(x, y, color="green")
    trend_plot.line(t, regression(t), color="red")

    script, div = components(trend_plot)
    plot_grid = ""

    return render_template(
        "results_polytrend.html",
        result=result_to_display,
        pt_map=plot_grid,
        script=script,
        div=div,
        is_point=True,
    )


def call_polytrend_polygon(dataset, alpha, band_name, ndvi_threshold):
    """ Splits the dataframe representing whole image into pixels
        Calls PolyTrend R package on time series of each pixel

    Args:
        dataset: Pandas dataframe 
            NDVI values per pixel, organized by geographic coordinates and date 
        alpha : float
            statistical significance of the fit specified by the user in home.html form

    Returns: 
        reduced_dataset : dataframe
            modified dataset reduced by the number of examined years. Contains for each pixel:
            geographic coordinates, trend type, linear trend slope, direction of change, significance

    """
    PT = importr("PolyTrend")
    PT_result = []
    # establish how many images there are in the collection
    list_of_images = dataset["id"]
    ids_of_images = []
    for img_id in list_of_images:
        if img_id not in ids_of_images:
            ids_of_images.append(img_id)

    n = len(ids_of_images)
    print("number of images: ", n)
    number_of_pixels = len(dataset)
    print("number of pixels analysed: ", number_of_pixels)
    # split the dataset into pixel time series
    for i in range(0, number_of_pixels, n):
        Y = dataset[i : i + n][band_name].values
        if all(val > ndvi_threshold for val in Y):
            vec = FloatVector(Y)
            result = list(PT.PolyTrend(Y=vec, alpha=alpha))
            # populate the empty PT_result list with values
            pixel_long = dataset.at[i, "longitude"]
            pixel_lat = dataset.at[i, "latitude"]
            geometry = [pixel_long, pixel_lat]
            PT_result_header = [
                "geometry",
                "trend_type",
                "slope",
                "direction",
                "significance",
            ]
            PT_result.append(
                [
                    geometry,
                    int(result[2][0]),
                    result[3][0],
                    int(result[4][0]),
                    int(result[5][0]),
                ]
            )
        else:
            print("!!!!!!!!!!!!!!! Unqualified value !!!!!!!!!!!!!!!!!!!!!!!!!!!!")
            pass

    # create a data frame for displaying results on a map
    reduced_dataset = pd.DataFrame(PT_result[0:], columns=PT_result_header)
    return reduced_dataset


def call_polytrend_point(dataset, alpha, band_name, ndvi_threshold):
    """ Calls PolyTrend function on a single geographical point
    
    Args:
        dataset: Pandas dataframe 
            NDVI values organized by date. Each value represents a time step in the same geographic point
        alpha : float
            statistical significance of the fit specified by the user in home.html form

    Returns: 
        reduced_dataset : dataframe
            modified dataset containing one pixel/ point with its
            geographic coordinates, trend type, linear trend slope, direction of change, significance

    """
    PT_result = []
    Y = dataset[band_name].values
    # check if Y qualifies
    if all(val > ndvi_threshold for val in Y):
        vec = FloatVector(Y)
        result = PolyTrend(vec, alpha)
        print("now change to df")
        return result
    else:
        # this will present a new screen with message that the values don't qualify
        print("Values below the threshold - probably water")
        exit()
    # populate the empty PT_result list
    pixel_long = dataset.at[0, "longitude"]
    pixel_lat = dataset.at[0, "latitude"]
    geometry = pixel_long, pixel_lat
    PT_result_header = [
        "geometry",
        "ts",
        "trend_type",
        "slope",
        "direction",
        "significance",
        "degree"
    ]
    print(result['trend_type'])
    try:
        PT_result.append(
            [
                geometry,
                Y,
                result['trend_type'],
                result['trend_type'], #change to slope value
                result['trend_type'], # change to direction
                result['significance'],
                result['polynomial_degree']
            ]
        )
        print("the result: ")
        print(PT_result)
        # create a data frame for displaying results on a map
        reduced_dataset = pd.DataFrame(PT_result[0:], columns=PT_result_header)
    except ValueError:
        print("value error")
        reduced_dataset = "value error"
    return reduced_dataset


def make_annual_composite(collection, start_year, end_year):
    # Create list of years
    years = ee.List.sequence(start_year, end_year, 1)

    def image_annual_composite(year_and_collection):
        year_and_collection = ee.List(year_and_collection)
        year = ee.Number(year_and_collection.get(0))
        _collection = ee.ImageCollection(year_and_collection.get(1))
        start_date = ee.Date.fromYMD(year, 1, 1)
        end_date = start_date.advance(1, "year")
        return (
            _collection.filterDate(start_date, end_date)
            .mean()
            .set("system:time_start", year)
        )

    # Create a list of year-collection pairs (i.e. pack the function inputs)
    list_of_years_and_collections = years.zip(
        ee.List.repeat(collection, years.length())
    )
    # calculate annual mean for each year-collection pair
    annual_ndvi = ee.ImageCollection.fromImages(
        list_of_years_and_collections.map(image_annual_composite)
    )
    return annual_ndvi


def do_polytrend(parameters):
    """ Get user defined parameters. Make an annual image composite. Derive time series from GEE.
        Analyze with PolyTrend. Visualize. 

        Called from .routes.py
    
    Args:
        parameters: dict 
            parameters for data and the algorithm specified by the user in home.html form 

    Returns: 
        plots 
            graphical output of Polytrend function, different for point (a single plot) 
            and for polygon (3 maps and descriptive statistics)

    """

    # Step 1: get all parameters entered by the user and transform them
    name_of_collection = parameters["dataset_name"]
    if name_of_collection == "NASA/GIMMS/3GV0":
        band_name = "ndvi"
        scale = 8000
        ndvi_threshold = 0.1
    elif name_of_collection == "MODIS/006/MOD13Q1_NDVI":
        name_of_collection = "MODIS/006/MOD13Q1"
        band_name = "NDVI"
        scale = 250
        ndvi_threshold = 1000
    elif name_of_collection == "MODIS/006/MOD13Q1_EVI":
        name_of_collection = "MODIS/006/MOD13Q1"
        band_name = "EVI"
        scale = 250
        ndvi_threshold = 1000
    coordinates = parameters["coordinates"]
    regex = re.sub("[\[\]]", "", coordinates)
    split = regex.split(",")
    coords = list(map(float, split))
    if len(coords) > 2:
        aoi = ee.Geometry.Polygon(coords)
        is_polygon = True
        is_point = False
    elif len(coords) == 2:
        aoi = ee.Geometry.Point(coords)
        is_point = True
        is_polygon = False
    else:
        print("wrong coordinates")

    start_year = parameters.get("from_year")
    end_year = parameters.get("to_year")
    start_date = start_year + "-01-01"
    end_date = end_year + "-12-31"
    start_year = int(start_year)
    end_year = int(end_year)
    img_collection = ee.ImageCollection(name_of_collection)
    crs = img_collection.first().getInfo()["bands"][0]["crs"]
    collection = img_collection.filterDate(start_date, end_date).filterBounds(aoi)
    save_ts_to_csv = parameters.get("save_ts_to_csv")
    save_result_to_csv = parameters.get("save_result_to_csv")
    name_of_csv_file_ts = parameters.get("name_of_csv_file_ts")
    name_of_csv_file_result = parameters.get("name_of_csv_file_result")

    is_polytrend = True
    alpha = parameters.get("alpha", type=float)
    try:
        crs = collection.first().getInfo()["bands"][0]["crs"]
    except TypeError:
        print("dataset empty")
        return render_template("error.html")

    # Setp 2: make an anual composite of image collections using mean value
    annual_ndvi = make_annual_composite(collection, start_year, end_year)

    # Depending on whether AOI is a point or polygon get a dataset, analyze it and visualize results
    if is_polygon:
        # Step 3: get numerical values from GEE as dataframe
        try:
            dataset = get_dataset_for_polygon(
                is_polytrend, annual_ndvi, aoi, scale, crs
            )
        except:
            message = "Sorry, couldn't get the data you requested. Possible problems: the dataset is too large (study area too large), study period is too long or the dataset for this period does not exist."
            return render_template("error.html", error_message=message)
        if save_ts_to_csv:
            dataset.to_csv(name_of_csv_file_ts + ".csv")
        # Step 4: analyze data using PolyTrend algorithm
        try:
            result = call_polytrend_polygon(dataset, alpha, band_name, ndvi_threshold)
        except:
            message = "Sorry, something went wrong inside the PolyTrend function."
            return render_template("error.html", error_message=message)
        if save_result_to_csv == "yes":
            result.to_csv(name_of_csv_file_result + ".csv")
        # Step 5: visualize results
        plots = visualize_polytrend_polygon(result)

    elif is_point:
        # Step 3: get numerical values from GEE as dataframe
        try:
            dataset = get_dataset_for_point(is_polytrend, annual_ndvi, aoi, scale, crs)
        except:
            message = "Sorry, couldn't get the data you requested. Possible problems: the dataset is too large (study area too large), study period is too long or the dataset for this period does not exist."
            return render_template("error.html", error_message=message)
        if save_ts_to_csv == "yes":
            dataset.to_csv(name_of_csv_file_ts)
        # Step 4: analyze data using PolyTrend algorithm
        try:
            result = call_polytrend_point(dataset, alpha, band_name, ndvi_threshold)
        except:
            message = "Sorry, something went wrong inside the PolyTrend function."
            return render_template("error.html", error_message=message)
        # Step 5: visualize results
        plots = visualize_polytrend_point(result, name_of_collection, start_year)

    return plots
