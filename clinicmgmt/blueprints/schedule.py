import uuid
from datetime import datetime
from datetime import timedelta
import time

from flask import Blueprint, request, make_response, redirect, url_for, render_template

from clinicmgmt.reusables.context import db_cursor
from clinicmgmt.reusables.context import db_connection
from clinicmgmt.reusables.context import website_context
from clinicmgmt.reusables.user_validation import get_user_context

from clinicmgmt.classes.Entry import Entry
from clinicmgmt.classes.EntryAuthor import EntryAuthor
from clinicmgmt.classes.EntryDeletedAuthor import EntryDeletedAuthor

schedule = Blueprint("schedule", __name__)


@schedule.route('/', methods=['GET', 'POST'])
def index():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    entry_db_lookup = tuple(db_cursor.execute("SELECT id, author_id, last_edit_author_id, assigned_doctor_id, "
                                              "patient_name, scheduled_timestamp, added_timestamp, "
                                              "last_edited_timestamp, type_of_surgery, diagnosis, patient_birth_year, "
                                              "patient_phone_number, has_consultation_happened, is_completed "
                                              "FROM patient_entries ORDER BY scheduled_timestamp ASC"))

    entries = []
    for entry in entry_db_lookup:
        current_entry = Entry(entry)
        current_entry_author = tuple(db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver "
                                                       "FROM users WHERE id = ?", [current_entry.author_id]))
        if current_entry_author:
            current_entry.author = EntryAuthor(current_entry_author[0])
        else:
            current_entry.author = EntryDeletedAuthor(current_entry.author_id)
        entries.append(current_entry)

    return make_response(
        render_template(
            "entry_listing.html",
            WEBSITE_CONTEXT=website_context,
            USER_CONTEXT=user_context,
            ENTRIES=entries
        )
    )


@schedule.route('/entry_maker_form')
def entry_maker_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template("entry_maker_form.html", WEBSITE_CONTEXT=website_context, USER_CONTEXT=user_context)


@schedule.route('/make_entry', methods=['POST'])
def make_entry():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if request.method == 'POST':
        patient_name = request.form['patient_name']
        assigned_doctor_id = request.form['assigned_doctor_id']
        html_timestamp = request.form['timestamp']
        type_of_surgery = request.form['type_of_surgery']
        diagnosis = request.form['diagnosis']
        patient_birth_year = request.form['patient_birth_year']
        patient_phone_number = request.form['patient_phone_number']
        has_consultation_happened = request.form['has_consultation_happened']

        if not patient_birth_year.isdigit():
            return "დაბადების წელი უნდა იყოს 4 რიცხვა ციფრი"

        scheduled_timestamp_input_datetime = datetime.strptime(html_timestamp, "%Y-%m-%dT%H:%M") - timedelta(
            seconds=website_context['timezone_offset']
        )
        scheduled_timestamp = int(scheduled_timestamp_input_datetime.timestamp())

        entry_id = uuid.uuid4()

        db_cursor.execute("INSERT INTO patient_entries "
                          "(id, author_id, last_edit_author_id, assigned_doctor_id, patient_name, scheduled_timestamp, "
                          "added_timestamp, last_edited_timestamp, type_of_surgery, diagnosis, patient_birth_year, "
                          "patient_phone_number, has_consultation_happened, is_completed) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          [str(entry_id), user_context.id, user_context.id, assigned_doctor_id, patient_name,
                           int(scheduled_timestamp),
                           int(time.time()), int(time.time()), type_of_surgery, diagnosis, int(patient_birth_year),
                           patient_phone_number, int(has_consultation_happened), 0])
        db_connection.commit()

        resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

        return resp


@schedule.route('/entry_view/<entry_id>')
def entry_view(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    entry_db_lookup = tuple(
        db_cursor.execute("SELECT id, author_id, last_edit_author_id, assigned_doctor_id, patient_name, "
                          "scheduled_timestamp, added_timestamp, last_edited_timestamp, type_of_surgery, diagnosis, "
                          "patient_birth_year, patient_phone_number, has_consultation_happened, is_completed "
                          "FROM patient_entries WHERE id = ? ", [entry_id]))
    if not entry_db_lookup:
        return "ჩანაწერი ვერ მოიძებნა. შეიძლება ადრე იყო და მერე წაშალა ვინმემ."

    entry = Entry(entry_db_lookup[0])
    entry_author = tuple(
        db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver FROM users WHERE id = ?",
                          [entry.author_id]))
    if entry_author:
        entry.author = EntryAuthor(entry_author[0])
    else:
        entry.author = EntryDeletedAuthor(entry.author_id)

    entry.approvers = []
    entry.current_user_has_approved = 0

    class Approver:
        def __init__(self, user_context_list, timestamp):
            self.id = str(user_context_list[0])
            self.display_name = str(user_context_list[2])
            self.approval_timestamp = timestamp

            approval_timestamp_tmp = datetime.fromtimestamp(self.approval_timestamp) + timedelta(
                seconds=website_context['timezone_offset'])
            self.approval_timestamp_str = approval_timestamp_tmp.strftime("%Y-%m-%d %H:%M")

    entry_approvals_db = tuple(db_cursor.execute("SELECT approver_author_id, approval_timestamp "
                                                 "FROM patient_doctor_approvals WHERE patient_id = ?", [entry_id]))

    for entry_approvals in entry_approvals_db:

        entry_approver_db = tuple(
            db_cursor.execute("SELECT id, email, display_name, is_administrator, is_approver FROM users WHERE id = ?",
                              [entry_approvals[0]]))
        if entry_approver_db:
            entry.approvers.append(Approver(entry_approver_db[0], entry_approvals[1]))
        else:
            entry.approvers.append(Approver([entry_approver_db[0], "წაშლილი მომხმარებელი"], entry_approvals[1]))

        if entry_approvals[0] == user_context.id:
            entry.current_user_has_approved = 1

    return render_template(
        "entry_view.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        ENTRY=entry
    )


@schedule.route('/entry_edit_form/<entry_id>')
def entry_edit_form(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    entry_db_lookup = tuple(
        db_cursor.execute("SELECT id, author_id, last_edit_author_id, assigned_doctor_id, patient_name, "
                          "scheduled_timestamp, added_timestamp, last_edited_timestamp, type_of_surgery, diagnosis, "
                          "patient_birth_year, patient_phone_number, has_consultation_happened, is_completed "
                          "FROM patient_entries WHERE id = ?", [entry_id]))

    if not entry_db_lookup:
        return "ჩანაწერი ვერ მოიძებნა. შეიძლება ადრე იყო და მერე წაშალა ვინმემ."

    entry = Entry(entry_db_lookup[0])

    return render_template(
        "entry_edit_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        ENTRY=entry
    )


@schedule.route('/delete_entry/<entry_id>')
def delete_entry(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    db_cursor.execute("DELETE FROM patient_entries WHERE id = ?", [entry_id])

    return redirect(url_for("schedule.index"))


@schedule.route('/edit_entry/<entry_id>', methods=['POST'])
def edit_entry(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if request.method == 'POST':
        patient_name = request.form['patient_name']
        assigned_doctor_id = request.form['assigned_doctor_id']
        timestamp = request.form['timestamp']
        type_of_surgery = request.form['type_of_surgery']
        diagnosis = request.form['diagnosis']
        patient_birth_year = request.form['patient_birth_year']
        patient_phone_number = request.form['patient_phone_number']
        has_consultation_happened = request.form['has_consultation_happened']
        is_completed = request.form['is_completed']

        if not patient_birth_year.isdigit():
            return "დაბადების წელი უნდა იყოს 4 რიცხვა ციფრი"

        scheduled_timestamp_input_datetime = datetime.strptime(timestamp, "%Y-%m-%dT%H:%M") - timedelta(
            seconds=website_context['timezone_offset']
        )
        scheduled_timestamp = int(scheduled_timestamp_input_datetime.timestamp())

        db_cursor.execute("UPDATE patient_entries "
                          "SET last_edit_author_id = ?, assigned_doctor_id = ?, patient_name = ?, "
                          "scheduled_timestamp = ?, last_edited_timestamp = ?, type_of_surgery = ?, "
                          "diagnosis = ?, patient_birth_year = ?, patient_phone_number = ?, "
                          "has_consultation_happened = ?, is_completed = ? WHERE id = ?",
                          [user_context.id, assigned_doctor_id, patient_name,
                           scheduled_timestamp, int(time.time()), type_of_surgery,
                           diagnosis, int(patient_birth_year), patient_phone_number,
                           has_consultation_happened, is_completed, entry_id])
        db_connection.commit()

        resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

        return resp


@schedule.route('/mark_entry_completed/<entry_id>')
def mark_entry_completed(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    db_cursor.execute("UPDATE patient_entries SET is_completed = ? WHERE id = ?", [1, entry_id])
    db_connection.commit()

    resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

    return resp


@schedule.route('/mark_entry_incomplete/<entry_id>')
def mark_entry_incomplete(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    db_cursor.execute("UPDATE patient_entries SET is_completed = ? WHERE id = ?", [0, entry_id])
    db_connection.commit()

    resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

    return resp


@schedule.route('/mark_entry_approved/<entry_id>')
def mark_entry_approved(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_approver == 1:
        return "თქვენ არ შეგიძლიათ თანხმობის გაცემა"

    already_approved = tuple(db_cursor.execute("SELECT patient_id FROM patient_doctor_approvals "
                                               "WHERE patient_id = ? AND approver_author_id = ?",
                                               [str(entry_id), str(user_context.id)]))

    if already_approved:
        return "თქვენ უკვე გაეცით თანხმობა ამ პაციენტზე."

    db_cursor.execute("INSERT INTO patient_doctor_approvals (patient_id, approver_author_id, approval_timestamp) "
                      "VALUES (?, ?, ?)", [str(entry_id), str(user_context.id), int(time.time())])
    db_connection.commit()

    resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

    return resp


@schedule.route('/mark_entry_disapproved/<entry_id>')
def mark_entry_disapproved(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))
    if not user_context.is_approver == 1:
        return "თქვენ არ შეგიძლიათ თანხმობის გაქუმება"

    db_cursor.execute("DELETE FROM patient_doctor_approvals WHERE patient_id = ? AND approver_author_id = ?",
                      [str(entry_id), str(user_context.id)])
    db_connection.commit()

    resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

    return resp


@schedule.route('/search_form')
def search_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template("search_form.html", WEBSITE_CONTEXT=website_context, USER_CONTEXT=user_context)
