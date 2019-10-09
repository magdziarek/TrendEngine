from flask import Flask, render_template, url_for, request, flash, Blueprint     
import jinja2
#for running R packages
from rpy2.robjects.packages import importr
#local imports
from TrendEngine.main.forms import DbestParametersForm, PolyTrendParametersForm 
from .dbest import dbest_func
from .polytrend import polytrend_func

### import R's utility package
## only has to be done the first time the application is run
# utils = importr('utils')
### select a mirror for R packages
# utils.chooseCRANmirror(ind=1) # select the first mirror in the list
# utils.install_packages('DBEST')
# utils.install_packages('PolyTrend')

calculations = Blueprint('calculations', __name__)

@calculations.route('/run_DBEST', methods=['GET', 'POST'])
def run_DBEST():
    """ Get user's input and send to dbest_func in dbest.py"""
    if request.method == 'POST':
        #parameters for datasets
        parameters = request.form

    print('params', parameters, type(parameters))
    result = dbest_func(parameters)
    return result

@calculations.route('/run_polytrend', methods=['GET', 'POST'])
def run_polytrend():
    """ Get user's input and send to polytrend_func in polytrend.py"""
    form = PolyTrendParametersForm()
    if form.validate_on_submit():
        flash('Please wait for results. It might take a few minutes...', 'success')
    else:
        flash('Please check your input is in the correct form suggested by the placeholders', 'danger')

    if request.method == 'POST':
        #parameters for datasets
        parameters = {}
        parameters["dataset_name"] = request.form['dataset_name']
        parameters["date_from"]= request.form['date_from']
        parameters["date_to"] = request.form['date_to']
        parameters["coordinates"] = request.form['coordinates']
        #parameters for PolyTrend
        parameters["alpha"] = request.form['alpha']
        parameters["save_result_to_csv"] = request.form['save_result_to_csv']
        parameters["save_ts_to_csv"] = request.form['save_ts_to_csv']

    result = polytrend_func(parameters)
    return result