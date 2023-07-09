from flask import Blueprint, request, redirect, url_for, render_template

from clinicmgmt.reusables.context import db_cursor
from clinicmgmt.reusables.context import db_connection
from clinicmgmt.reusables.context import website_context
from clinicmgmt.reusables.user_validation import get_user_context

administration = Blueprint("administration", __name__)


@administration.route('/administration')
def admin():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return "ამის უფლება მხოლოდ ადმინისტრატორს აქვს."

    return render_template("admin_panel.html", WEBSITE_CONTEXT=website_context, USER_CONTEXT=user_context)


@administration.route('/administration/sql_form')
def sql_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return "ამის უფლება მხოლოდ ადმინისტრატორს აქვს."

    return render_template(
        "sql.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context
    )


@administration.route('/administration/sql_exec', methods=['POST'])
def sql_exec():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return "ამის უფლება მხოლოდ ადმინისტრატორს აქვს."

    if request.method == 'POST':
        sql_query = request.form['sql_query']

        sql_results = tuple(db_cursor.execute(sql_query))
        db_connection.commit()

        return render_template(
            "sql.html",
            WEBSITE_CONTEXT=website_context,
            USER_CONTEXT=user_context,
            SQL_RESULTS=sql_results
        )


@administration.route('/user_list')
def user_listing():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    # if not user_context.is_administrator == 1:
    #     return "ამის უფლება მხოლოდ ადმინისტრატორს აქვს."

    info_db = tuple(db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver FROM users"))
    return render_template(
        "user_listing.html",
        WEBSITE_CONTEXT=website_context,
        USER_LISTING=info_db,
        USER_CONTEXT=user_context
    )
