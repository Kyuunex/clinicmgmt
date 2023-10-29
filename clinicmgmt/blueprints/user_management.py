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
from clinicmgmt.reusables.context import LANG_STRINGS
from clinicmgmt.reusables.user_validation import get_user_context
from clinicmgmt.reusables.user_validation import validate_user_credentials

from clinicmgmt.classes.Invite import Invite
from clinicmgmt.classes.InviteAuthor import InviteAuthor
from clinicmgmt.classes.EntryDeletedAuthor import EntryDeletedAuthor

user_management = Blueprint("user_management", __name__)


@user_management.route('/account_settings')
def account_settings():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template(
        "account_settings.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/login_form')
def login_form():
    user_context = get_user_context()
    if user_context:
        return redirect(url_for("schedule.index"))

    is_anyone_registered = tuple(db_cursor.execute("SELECT id FROM users"))

    return render_template(
        "login_form.html",
        WEBSITE_CONTEXT=website_context,
        IS_ANYONE_REGISTERED=is_anyone_registered,
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/registration_form')
def registration_form():
    is_anyone_registered = tuple(db_cursor.execute("SELECT id FROM users"))
    invite_code = None
    invite_db_query = None

    if is_anyone_registered:
        invite_code = request.args.get('invite_code')
        if invite_code:
            invite_db_query = tuple(db_cursor.execute("SELECT invite_code FROM invite_codes "
                                                      "WHERE invite_code = ? AND expiry_timestamp > ?",
                                                      [invite_code, int(time.time())]))
            if not invite_db_query:
                return LANG_STRINGS.INVITE_CODE_IS_INVALID

        if not invite_db_query:
            return LANG_STRINGS.INVITE_CODE_REQUIRED_CONTACT_ADMIN

    user_context = get_user_context()
    if user_context:
        return redirect(url_for("schedule.index"))

    return render_template(
        "registration_form.html",
        WEBSITE_CONTEXT=website_context,
        INVITE_CODE=invite_code,
        LANG_STRINGS=LANG_STRINGS
    )


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
                NOTICE_MESSAGE=LANG_STRINGS.WRONG_EMAIL_OR_PASSWORD,
                ALERT_TYPE="alert-danger",
                LANG_STRINGS=LANG_STRINGS
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
        invite_code = request.form.get('invite_code')
        email = request.form['email']

        is_anyone_registered = tuple(db_cursor.execute("SELECT id FROM users"))

        validate_invite = tuple(db_cursor.execute("SELECT invite_code FROM invite_codes "
                                                  "WHERE invite_code = ? AND invitee_email = ? AND expiry_timestamp > ?",
                                                  [invite_code, email.strip().lower(), int(time.time())]))

        if not validate_invite:
            if is_anyone_registered:
                return LANG_STRINGS.TO_REGISTER_CONTACT_ADMIN

        display_name = request.form['display_name']

        password = request.form['password']
        repeat_password = request.form['repeat_password']

        if not password == repeat_password:
            return LANG_STRINGS.PASSWORDS_DONT_MATCH_TRY_REGISTRATION_AGAIN

        password_salt = get_random_string(32)

        hashed_password = hashlib.sha256((password + password_salt).encode()).hexdigest()

        if not is_anyone_registered:
            is_administrator = 1
            is_approver = 1
            page_after_registration = "administration.website_configuration_form"
        else:
            is_administrator = 0
            is_approver = 0
            page_after_registration = "schedule.index"

        email_already_taken = tuple(db_cursor.execute("SELECT id FROM users WHERE email = ? COLLATE NOCASE",
                                                      [email.strip().lower()]))

        if email_already_taken:
            return LANG_STRINGS.EMAIL_ALREADY_TAKEN_CONTACT_ADMIN_FOR_HELP

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
        resp = make_response(redirect(url_for(page_after_registration)))
        resp.set_cookie('session_token', new_session_token, max_age=34560000)
        token_id = uuid.uuid4()
        expiry_timestamp = int(time.time()) + 34560000
        hashed_token = hashlib.sha256(new_session_token.encode()).hexdigest()
        client_ip_address_is_ipv6, client_ip_address_int = ip_decode(request)
        db_cursor.execute("INSERT INTO session_tokens VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                          [str(user_id), str(token_id), hashed_token, int(time.time()), expiry_timestamp,
                           str(request.user_agent.string), int(client_ip_address_int), int(client_ip_address_is_ipv6)])
        db_cursor.execute("DELETE FROM invite_codes WHERE invitee_email = ? AND invite_code = ?",
                          [email.strip().lower(), str(invite_code)])
        db_connection.commit()

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
        timezone=timezone,
        LANG_STRINGS=LANG_STRINGS
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

    return render_template(
        "password_change_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/change_password_attempt', methods=['POST'])
def change_password_attempt():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    old_password = request.form['old_password']
    new_password = request.form['new_password']
    repeat_new_password = request.form['repeat_new_password']

    if not new_password == repeat_new_password:
        return render_template(
            "account_settings.html",
            WEBSITE_CONTEXT=website_context,
            USER_CONTEXT=user_context,
            NOTICE_MESSAGE=LANG_STRINGS.NEW_PASSWORDS_DONT_MATCH,
            ALERT_TYPE="alert-danger",
            LANG_STRINGS=LANG_STRINGS
        )

    old_password_salt_db = tuple(db_cursor.execute("SELECT password_salt FROM user_passwords WHERE user_id = ?",
                                                   [user_context.id]))
    if not old_password_salt_db:
        # This should never happen
        return LANG_STRINGS.UNKNOWN_ERROR_HAS_OCCURRED

    old_password_salt = old_password_salt_db[0][0]

    old_hashed_password = hashlib.sha256((old_password + old_password_salt).encode()).hexdigest()

    db_query = tuple(db_cursor.execute("SELECT user_id FROM user_passwords WHERE user_id = ? AND password_hash = ?",
                                       [user_context.id, old_hashed_password]))
    if not db_query:
        return render_template(
            "account_settings.html",
            WEBSITE_CONTEXT=website_context,
            USER_CONTEXT=user_context,
            NOTICE_MESSAGE=LANG_STRINGS.OLD_PASSWORD_IS_INCORRECT,
            ALERT_TYPE="alert-danger",
            LANG_STRINGS=LANG_STRINGS
        )

    db_cursor.execute("DELETE FROM user_passwords WHERE user_id = ? AND password_hash = ? AND password_salt = ?",
                      [str(user_context.id), str(old_hashed_password), old_password_salt])

    new_password_salt = get_random_string(32)

    new_hashed_password = hashlib.sha256((new_password + new_password_salt).encode()).hexdigest()

    db_cursor.execute("INSERT INTO user_passwords (user_id, password_hash, password_salt) VALUES (?, ?, ?)",
                      [str(user_context.id), str(new_hashed_password), new_password_salt])
    db_connection.commit()

    return render_template(
        "account_settings.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.PASSWORD_CHANGED_SUCCESSFULLY,
        ALERT_TYPE="alert-success",
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/member_invite_form')
def member_invite_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    return render_template(
        "member_invite_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/member_invite_generate', methods=['POST'])
def member_invite_generate():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    invitee_email = request.form['email']

    invite_code = uuid.uuid4()

    db_cursor.execute("INSERT INTO invite_codes (invite_code, invitee_email, inviter_id, "
                      "generation_timestamp, expiry_timestamp) VALUES (?, ?, ?, ?, ?)",
                      [str(invite_code), str(invitee_email.strip().lower()), str(user_context.id),
                       int(time.time()), int(time.time() + (30 * 86400))])
    db_connection.commit()

    invite_listing_db = tuple(db_cursor.execute("SELECT invite_code, invitee_email, inviter_id, "
                                                "generation_timestamp, expiry_timestamp "
                                                "FROM invite_codes ORDER BY generation_timestamp DESC"))

    invite_listing = []
    for entry in invite_listing_db:
        current_invite = Invite(entry)
        current_invite_author = tuple(db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver "
                                                        "FROM users WHERE id = ?", [current_invite.inviter_id]))
        if current_invite_author:
            current_invite.author = InviteAuthor(current_invite_author[0])
        else:
            current_invite.author = EntryDeletedAuthor(current_invite.inviter_id)
        invite_listing.append(current_invite)

    return render_template(
        "invitee_listing.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.INVITE_CREATED_MESSAGE % (
            invitee_email,
            request.host_url[:-1] + url_for('user_management.registration_form', invite_code=invite_code)
        ),
        ALERT_TYPE="alert-success",
        INVITE_LISTING=invite_listing,
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/member_invite_listing')
def member_invite_listing():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    invite_listing_db = tuple(db_cursor.execute("SELECT invite_code, invitee_email, inviter_id, "
                                                "generation_timestamp, expiry_timestamp "
                                                "FROM invite_codes ORDER BY generation_timestamp DESC"))

    invite_listing = []
    for entry in invite_listing_db:
        current_invite = Invite(entry)
        current_invite_author = tuple(db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver "
                                                        "FROM users WHERE id = ?", [current_invite.inviter_id]))
        if current_invite_author:
            current_invite.author = InviteAuthor(current_invite_author[0])
        else:
            current_invite.author = EntryDeletedAuthor(current_invite.inviter_id)
        invite_listing.append(current_invite)

    return render_template(
        "invitee_listing.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        INVITE_LISTING=invite_listing,
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/destroy_invite', methods=['GET'])
def destroy_invite():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    invite_code = request.args.get('invite_code')

    db_cursor.execute("DELETE FROM invite_codes WHERE invite_code = ?", [invite_code])
    db_connection.commit()

    return render_template(
        "invitee_listing.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.INVITE_HAS_BEEN_DELETED,
        ALERT_TYPE="alert-success",
        INVITE_LISTING=[],
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/administrator_password_recovery_form')
def administrator_password_recovery_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    user_id = request.args.get('user_id')
    user_lookup_db = tuple(db_cursor.execute("SELECT email, display_name, is_administrator FROM users WHERE id = ?", [user_id]))
    if not user_lookup_db:
        return "you are using this endpoint incorrectly"

    if bool(user_lookup_db[0][2]):
        return LANG_STRINGS.ADMIN_CANT_RECOVER_OTHER_ADMIN_ACCOUNT

    return render_template(
        "administrator_password_recovery_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        USER_ID=user_id,
        USER_EMAIL=user_lookup_db[0][0],
        USER_DISPLAY_NAME=user_lookup_db[0][1],
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/administrator_password_recovery_attempt', methods=['POST'])
def administrator_password_recovery_attempt():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    user_id = request.form['user_id']
    new_password = request.form['new_password']
    repeat_new_password = request.form['repeat_new_password']

    if not new_password == repeat_new_password:
        return render_template(
            "account_settings.html",
            WEBSITE_CONTEXT=website_context,
            USER_CONTEXT=user_context,
            NOTICE_MESSAGE=LANG_STRINGS.NEW_PASSWORDS_DONT_MATCH,
            ALERT_TYPE="alert-danger",
            LANG_STRINGS=LANG_STRINGS
        )

    db_cursor.execute("DELETE FROM user_passwords WHERE user_id = ?",
                      [str(user_id)])

    new_password_salt = get_random_string(32)

    new_hashed_password = hashlib.sha256((new_password + new_password_salt).encode()).hexdigest()

    db_cursor.execute("INSERT INTO user_passwords (user_id, password_hash, password_salt) VALUES (?, ?, ?)",
                      [str(user_id), str(new_hashed_password), new_password_salt])
    db_connection.commit()

    return render_template(
        "admin_panel.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.PASSWORD_CHANGED_SUCCESSFULLY,
        ALERT_TYPE="alert-success",
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/administrator_account_deletion_form')
def administrator_account_deletion_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    user_id = request.args.get('user_id')
    user_lookup_db = tuple(db_cursor.execute("SELECT email, display_name, is_administrator FROM users WHERE id = ?", [user_id]))
    if not user_lookup_db:
        return "you are using this endpoint incorrectly"

    if bool(user_lookup_db[0][2]):
        return LANG_STRINGS.ADMIN_CANT_DELETE_ANOTHER_ADMIN_ACCOUNT

    return render_template(
        "administrator_account_deletion_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        USER_ID=user_id,
        USER_EMAIL=user_lookup_db[0][0],
        USER_DISPLAY_NAME=user_lookup_db[0][1],
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/administrator_account_deletion_attempt', methods=['POST'])
def administrator_account_deletion_attempt():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    user_id = request.form['user_id']

    db_cursor.execute("DELETE FROM users WHERE id = ?", [str(user_id)])
    db_cursor.execute("DELETE FROM session_tokens WHERE user_id = ?", [str(user_id)])
    db_cursor.execute("DELETE FROM user_passwords WHERE user_id = ?", [str(user_id)])

    return render_template(
        "admin_panel.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.USER_DELETED_SUCCESSFULLY,
        ALERT_TYPE="alert-success",
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/administrator_account_editing_form')
def administrator_account_editing_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    user_id = request.args.get('user_id')
    user_lookup_db = tuple(db_cursor.execute("SELECT email, display_name, is_administrator, is_approver "
                                             "FROM users WHERE id = ?", [user_id]))
    if not user_lookup_db:
        return "you are using this endpoint incorrectly"

    return render_template(
        "administrator_account_editing_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        USER_ID=user_id,
        USER_EMAIL=user_lookup_db[0][0],
        USER_DISPLAY_NAME=user_lookup_db[0][1],
        USER_IS_ADMINISTRATOR=user_lookup_db[0][2],
        USER_IS_APPROVER=user_lookup_db[0][3],
        LANG_STRINGS=LANG_STRINGS
    )


@user_management.route('/administrator_account_editing_attempt', methods=['POST'])
def administrator_account_editing_attempt():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if not user_context.is_administrator == 1:
        return LANG_STRINGS.ONLY_ADMINISTRATOR_HAS_THE_PERMISSIONS_TO_DO_THIS

    user_id = request.form['user_id']
    email = request.form['email']
    display_name = request.form['display_name']
    is_approver = request.form['is_approver']
    is_administrator = request.form['is_administrator']

    db_cursor.execute("UPDATE users SET email = ? , display_name = ? , is_administrator = ? , is_approver = ? "
                      "WHERE id = ?",
                      [str(email.strip().lower()), str(display_name), int(is_administrator), int(is_approver),
                       str(user_id)])
    db_connection.commit()

    return render_template(
        "admin_panel.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        NOTICE_MESSAGE=LANG_STRINGS.USER_SUCCESSFULLY_UPDATED,
        ALERT_TYPE="alert-success",
        LANG_STRINGS=LANG_STRINGS
    )
