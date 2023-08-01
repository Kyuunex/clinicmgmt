from flask import Blueprint, request, make_response, redirect, url_for, render_template

import hashlib
import ipaddress
import time
import uuid
from datetime import datetime, timezone

from clinicmgmt.reusables.rng import get_random_string
from clinicmgmt.reusables.iptools import ip_decode
from clinicmgmt.reusables.context import db_cursor
from clinicmgmt.reusables.context import db_connection
from clinicmgmt.reusables.context import website_context
from clinicmgmt.reusables.user_validation import get_user_context
from clinicmgmt.reusables.user_validation import validate_user_credentials
from clinicmgmt.reusables.user_validation import validate_invite
from clinicmgmt.reusables.user_validation import delete_invite

user_management = Blueprint("user_management", __name__)


@user_management.route('/account_settings')
def account_settings():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template("account_settings.html", WEBSITE_CONTEXT=website_context, USER_CONTEXT=user_context)


@user_management.route('/login_form')
def login_form():
    user_context = get_user_context()
    if user_context:
        return redirect(url_for("schedule.index"))

    is_anyone_registered = tuple(db_cursor.execute("SELECT id FROM users"))
    is_registration_enabled = tuple(db_cursor.execute(
        "SELECT value FROM app_configuration WHERE setting = ?", ["allow_registration"])
    )

    allow_registration = True
    if not is_registration_enabled:
        if is_anyone_registered:
            allow_registration = False

    return render_template("login_form.html", WEBSITE_CONTEXT=website_context, ALLOW_REGISTRATION=allow_registration)


@user_management.route('/registration_form')
def registration_form():
    is_anyone_registered = tuple(db_cursor.execute("SELECT id FROM users"))
    is_registration_enabled = tuple(db_cursor.execute(
        "SELECT value FROM app_configuration WHERE setting = ?", ["allow_registration"])
    )

    if not is_registration_enabled:
        if is_anyone_registered:
            return "დასარეგისტრირებლად გთხოვთ მიმართოთ ადმინისტრატორს."

    user_context = get_user_context()
    if user_context:
        return redirect(url_for("schedule.index"))

    return render_template("registration_form.html", WEBSITE_CONTEXT=website_context)


@user_management.route('/login_attempt', methods=['POST'])
def login_attempt():
    if get_user_context():
        return redirect(url_for("schedule.index"))

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user_id = validate_user_credentials(email.strip().lower(), password)
        if not user_id:
            return render_template(
                "login_form.html",
                WEBSITE_CONTEXT=website_context,
                NOTICE_MESSAGE="არასწორი ელ.ფოსტა ან პაროლი არის მითითებული",
                ALERT_TYPE="alert-danger"
            )

        new_session_token = get_random_string(32)
        resp = make_response(redirect(url_for("schedule.index")))

        if bool(request.form.get('remember_me', 0)):
            cookie_age = 34560000
            expiry_timestamp = int(time.time()) + cookie_age
        else:
            cookie_age = None
            expiry_timestamp = int(time.time()) + 172800

        resp.set_cookie('session_token', new_session_token, max_age=cookie_age)

        hashed_token = hashlib.sha256(new_session_token.encode()).hexdigest()
        client_ip_address_is_ipv6, client_ip_address_int = ip_decode(request)
        token_id = uuid.uuid4()

        db_cursor.execute("INSERT INTO session_tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          [str(user_id), str(token_id), hashed_token,
                           int(time.time()), expiry_timestamp, str(request.user_agent.string),
                           int(client_ip_address_int), int(client_ip_address_is_ipv6)])
        db_connection.commit()
        return resp


@user_management.route('/registration_attempt', methods=['POST'])
def registration_attempt():
    if get_user_context():
        return redirect(url_for("schedule.index"))

    if request.method == 'POST':
        invite_code = request.form['invite_code']
        email = request.form['email']

        is_anyone_registered = tuple(db_cursor.execute("SELECT id FROM users"))

        if not validate_invite(invite_code, email.strip().lower()):
            if is_anyone_registered:
                return "დასარეგისტრირებლად გთხოვთ მიმართოთ ადმინისტრატორს."

        display_name = request.form['display_name']

        password = request.form['password']
        repeat_password = request.form['repeat_password']

        if not password == repeat_password:
            return "პაროლები არ ემთხვევა, ცადეთ რეგისტრაცია ახლიდან."

        password_salt = get_random_string(32)

        hashed_password = hashlib.sha256((password + password_salt).encode()).hexdigest()

        if not is_anyone_registered:
            is_administrator = 1
            is_approver = 1
        else:
            is_administrator = 0
            is_approver = 0

        email_already_taken = tuple(db_cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE",
                                                      [email.strip().lower()]))

        if email_already_taken:
            return "ამ ელ.ფოსტით უკვე არის დარეგისტრირებული მომხმარებელი. თუ ვერ შედიხართ, მიმართეთ ადმინისტრატორს."

        user_id = uuid.uuid4()

        db_cursor.execute("INSERT INTO users "
                          "(id, email, display_name, is_administrator, is_approver) VALUES (?, ?, ?, ?, ?)",
                          [str(user_id), str(email.strip().lower()), str(display_name.strip()),
                           int(is_administrator), int(is_approver)])
        db_connection.commit()

        db_cursor.execute("INSERT INTO user_passwords (user_id, password_hash, password_salt) VALUES (?, ?, ?)",
                          [str(user_id), str(hashed_password), str(password_salt)])
        db_connection.commit()

        new_session_token = get_random_string(32)
        resp = make_response(redirect(url_for("schedule.index")))
        resp.set_cookie('session_token', new_session_token, max_age=34560000)
        token_id = uuid.uuid4()
        expiry_timestamp = int(time.time()) + 34560000
        hashed_token = hashlib.sha256(new_session_token.encode()).hexdigest()
        client_ip_address_is_ipv6, client_ip_address_int = ip_decode(request)
        db_cursor.execute("INSERT INTO session_tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          [str(user_id), str(token_id), hashed_token, int(time.time()), expiry_timestamp,
                           str(request.user_agent.string), int(client_ip_address_int), int(client_ip_address_is_ipv6)])
        db_connection.commit()
        delete_invite(invite_code, email.strip().lower())

        return resp


@user_management.route('/logout')
def logout():
    if not get_user_context():
        return redirect(url_for("user_management.login_form"))

    resp = make_response(redirect(url_for("user_management.login_form")))
    resp.set_cookie('session_token', '', max_age=34560000)

    hashed_token = hashlib.sha256((request.cookies['session_token']).encode()).hexdigest()

    db_cursor.execute("DELETE FROM session_tokens WHERE token = ?", [hashed_token])
    db_connection.commit()
    return resp


@user_management.route('/session_listing')
def session_listing_page():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    session_listing = tuple(db_cursor.execute("SELECT token, timestamp, user_agent, ip_address, is_ipv6, "
                                              "token_id, expiry_timestamp "
                                              "FROM session_tokens WHERE user_id = ?"
                                              "ORDER BY timestamp DESC", [user_context.id]))

    return render_template(
        "session_listing.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        SESSION_LISTING=session_listing,
        datetime=datetime,
        ipaddress=ipaddress,
        timezone=timezone
    )


@user_management.route('/destroy_session_token', methods=['GET'])
def destroy_session_token():
    if not get_user_context():
        return redirect(url_for("user_management.login_form"))

    resp = make_response(redirect(url_for("user_management.session_listing_page")))

    token_id = request.args.get('token_id')

    db_cursor.execute("DELETE FROM session_tokens WHERE token_id = ?", [token_id])
    db_connection.commit()
    return resp


@user_management.route('/change_password_form')
def change_password_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template("password_change_form.html", WEBSITE_CONTEXT=website_context, USER_CONTEXT=user_context)


@user_management.route('/change_password_attempt', methods=['POST'])
def change_password_attempt():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return "სადემონსტრაციო ვერსიაში არ არის ეს ფუნქცია"



@user_management.route('/memeber_invite_form')
def memeber_invite_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template("member_invite_form.html", WEBSITE_CONTEXT=website_context, USER_CONTEXT=user_context)


@user_management.route('/memeber_invite_generate', methods=['POST'])
def memeber_invite_generate():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return "სადემონსტრაციო ვერსიაში არ არის ეს ფუნქცია"
