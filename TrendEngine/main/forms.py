from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, SelectField, DateField, IntegerField, DecimalField, TextAreaField
from wtforms.validators import DataRequired


class DbestParametersForm(FlaskForm):
	#selecting time series
	dataset_name = SelectField('Dataset', choices=[("NASA/GIMMS/3GV0", "GIMMS 8000m"), ("MODIS/006/MOD13Q1_NDVI", "MODIS NDVI 250 m"), 
		("MODIS/006/MOD13Q1_EVI", "MODIS EVI 250m")])
	user_dataset_name = StringField('Own dataset/ GEE asset')
	date_from = DateField('Date from', format='%Y-%m-%d', validators=[DataRequired()])
	date_to = DateField('Date to', format='%Y-%m-%d', validators=[DataRequired()])
	coordinates = DecimalField('Coordinates', validators=[DataRequired()])
	#DBEST parameters
	data_type = SelectField('Data type', choices=[('cyclical', 'cyclical'), ('non-cyclical', 'non-cyclical')])
	algorithm = SelectField('Algorithm', choices=[('change detection', 'change detection'), ('generalization', 'generalization')])
	breakpoint_no = IntegerField('Number of breakpoints', default=3)
	seasonality = IntegerField('Seasonality', default=12)
	first_level_shift = DecimalField('First level shift value', rounding=None, places=3, default=0.1)
	second_level_shift = DecimalField('Second level shift value', rounding=None, places=3, default=0.2)
	distance = StringField('Distance threshold', default='default')
	duration = IntegerField('Duration', default=24)
	alpha = DecimalField('Alpha', rounding=None, places=2, default=0.05)

	save_ts_to_csv = SelectField('Save time series to file (time_series.csv)', choices=[(False, 'No'), (True, 'Yes')], default=False)
	save_result_to_csv = SelectField('Save result to file (DBEST_result.csv)', choices=[(False, 'No'), (True, 'Yes')], default=False)

	submit = SubmitField('Submit')

class PolyTrendParametersForm(FlaskForm):
	#selecting time series
	date_description = TextAreaField(u'For MODIS no earlier than 2000-03-01, for GIMMS 1981-07-01')
	dataset_name = SelectField('Dataset', choices=[("NASA/GIMMS/3GV0", "GIMMS 8000m"), ("MODIS/006/MOD13Q1_NDVI", "MODIS NDVI 250 m"),
		("MODIS/006/MOD13Q1_EVI", "MODIS EVI 250m")], validators=[DataRequired()])
	user_dataset_name = StringField('Own dataset/ GEE asset')
	date_from = DateField('Date from', format='%d-%m-%Y', validators=[DataRequired()])
	date_to = DateField('Date to', format='%d-%m-%Y', validators=[DataRequired()])
	coordinates = DecimalField('Coordinates', validators=[DataRequired()])
	#PolyTrend parameters
	alpha = DecimalField('Alpha', rounding=None, places=2, default=0.05)

	save_ts_to_csv = SelectField('Save time series to file (time_series.csv)', choices=[(False, 'No'), (True, 'Yes')], default=False)
	save_result_to_csv = SelectField('Save result to file PolyTrend_result.csv', choices=[(False, 'No'), (True, 'Yes')], default=False)

	submit = SubmitField('Submit')

