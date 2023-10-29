from flask import Blueprint, request, redirect, url_for, render_template

from clinicmgmt.reusables.context import db_cursor
from clinicmgmt.reusables.context import db_connection
from clinicmgmt.reusables.context import website_context
from clinicmgmt.reusables.context import LANG_STRINGS
from clinicmgmt.reusables.user_validation import get_user_context
from clinicmgmt.reusables.constants import ALL_TIMEZONES
from clinicmgmt.reusables.constants import SUPPORTED_LANGUAGES

from clinicmgmt.classes.WebsiteConfig import *

administration = Blueprint("administration", __name__)


@administration.route('/administration')
def admin():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    return render_template(
        "admin_panel.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@administration.route('/administration/sql_form')
def sql_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    return render_template(
        "sql.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@administration.route('/administration/sql_exec', methods=['POST'])
def sql_exec():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    if request.method == 'POST':
        sql_query = request.form['sql_query']

        sql_results = tuple(db_cursor.execute(sql_query))
        db_connection.commit()

        return render_template(
            "sql.html",
            WEBSITE_CONTEXT=website_context,
            USER_CONTEXT=user_context,
            SQL_RESULTS=sql_results,
            LANG_STRINGS=LANG_STRINGS
        )


@administration.route('/user_list')
def user_listing():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    # if not user_context.is_administrator == 1:
    #     return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    info_db = tuple(db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver FROM users"))
    return render_template(
        "user_listing.html",
        WEBSITE_CONTEXT=website_context,
        USER_LISTING=info_db,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@administration.route('/website_configuration_form')
def website_configuration_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    config_db = tuple(db_cursor.execute("SELECT setting, value FROM app_configuration"))

    config = WebsiteConfig(config_db)

    return render_template(
        "admin_website_configuration_form.html",
        WEBSITE_CONTEXT=website_context,
        CONFIG=config,
        USER_CONTEXT=user_context,
        ALL_TIMEZONES=ALL_TIMEZONES,
        SUPPORTED_LANGUAGES=SUPPORTED_LANGUAGES,
        LANG_STRINGS=LANG_STRINGS
    )


@administration.route('/update_website_config', methods=['POST'])
def update_website_config():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    title = request.form['title']
    timezone_str = request.form['timezone_str']
    language = request.form['language']

    db_cursor.execute("INSERT OR REPLACE INTO app_configuration (setting, value) VALUES (?, ?)", ["title", title])

    db_cursor.execute("INSERT OR REPLACE INTO app_configuration (setting, value) VALUES (?, ?)",
                      ["timezone_str", timezone_str])

    db_cursor.execute("INSERT OR REPLACE INTO app_configuration (setting, value) VALUES (?, ?)",
                      ["language", language])

    db_connection.commit()

    return render_template(
        "admin_panel.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.CONFIG_SAVED_RESTART_TO_APPLY,
        ALERT_TYPE="alert-info",
        LANG_STRINGS=LANG_STRINGS
    )
