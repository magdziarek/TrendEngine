"""
    TrendEngine
    ~~~~~
    A tool to analyze remote sensing time series data. 
    Uses Google Earth Engine API for obtaining datasets. 

    :copyright: 2019 Aleksandra Magdziarek
    :license: MIT
"""

from flask import Flask
from TrendEngine.calculations.routes import calculations
from TrendEngine.main.routes import main

app = Flask(__name__)
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde280ba245'

app.register_blueprint(calculations)
app.register_blueprint(main)