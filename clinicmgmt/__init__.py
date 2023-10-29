#!/usr/bin/env python3

from flask import Flask, url_for, redirect, render_template

from clinicmgmt.reusables.context import db_connection
from clinicmgmt.reusables.context import website_context
from clinicmgmt.reusables.context import LANG_STRINGS
from clinicmgmt.reusables.user_validation import get_user_context

from clinicmgmt.blueprints.administration import administration
from clinicmgmt.blueprints.schedule import schedule
from clinicmgmt.blueprints.user_management import user_management

app = Flask(__name__)
app.register_blueprint(administration)
app.register_blueprint(schedule)
app.register_blueprint(user_management)


@app.route('/server_shutdown')
def server_shutdown():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMIN_HAS_PERMISSIONS_TO_TURN_OFF_THE_SITE

    db_connection.commit()
    db_connection.close()

    return LANG_STRINGS.SERVER_IS_READY_FOR_SHUTDOWN


@app.route('/cookies')
def cookies():
    user_context = get_user_context()
    return render_template(
        "cookies.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )
