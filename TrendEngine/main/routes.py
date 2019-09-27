from flask import Flask, Blueprint, render_template, url_for, request, flash 
from .forms import DbestParametersForm, PolyTrendParametersForm     
import jinja2

from .forms import DbestParametersForm, PolyTrendParametersForm     

main = Blueprint('main', __name__)

@main.route("/", methods=['GET', 'POST'])
def home():
    DBEST_form = DbestParametersForm()
    PolyTrend_form = PolyTrendParametersForm()
    return render_template(
        "home.html", 
        DBEST_form=DBEST_form, 
        PolyTrend_form=PolyTrend_form)

@main.route("/help")
def help():
    return render_template('help.html')