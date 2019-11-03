from flask import Flask, render_template, url_for, request, flash, Blueprint
import jinja2

# for running R packages
from rpy2.robjects.packages import importr

# local imports
from .dbest import dbest_func
from .polytrend import polytrend_func

### import R's utility package
## only has to be done the first time the application is run
# utils = importr('utils')
### select a mirror for R packages
# utils.chooseCRANmirror(ind=1) # select the first mirror in the list
# utils.install_packages('DBEST')
# utils.install_packages('PolyTrend')

calculations = Blueprint("calculations", __name__)


@calculations.route("/result", methods=["GET", "POST"])
def get_result():
    """ Get user's input and send to polytrend_func in polytrend.py"""

    if request.method == "POST":
        # parameters for datasets
        parameters = request.form

    if parameters["isDbest"] == "yes":
        result = do_dbest(parameters)
        print("Is dbest?", parameters["isDbest"])
    elif parameters["isPolytrend"] == "yes":
        result = do_polytrend(parameters)
        print("is polytrend?", parameters["isPolytrend"])
    return result
