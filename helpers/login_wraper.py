from functools import wraps

from flask import session, request, flash, redirect, url_for
import logging
from datetime import datetime


def test_login_session_is_ok_or_not(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if session.get("logged_in"):
            logging.info(f"[+] IP {request.remote_addr} Succsessfully income in {func.__name__} at {datetime.now()}")
            return func(*args, **kwargs)

        logging.info(f"[-] IP {request.remote_addr} try connect unSuccsessfully at {datetime.now()}")
        flash("wrong autentication")
        return redirect(url_for('index'))

    return wrapper
