from flask import request
from datetime import datetime


def get_user_dates_or_return_today():
    """
        If user enter valid date get it else return currect date
    """
    f_data = request.form["fdata"] or str(datetime.today().date())
    l_data = request.form["ldata"] or str(datetime.today().date())
    return f_data, l_data
