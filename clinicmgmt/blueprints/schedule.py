import uuid
from datetime import datetime
import time

from flask import Blueprint, request, make_response, redirect, url_for, render_template

from clinicmgmt.reusables.context import db_cursor
from clinicmgmt.reusables.context import db_connection
from clinicmgmt.reusables.context import website_context
from clinicmgmt.reusables.context import LANG_STRINGS
from clinicmgmt.reusables.user_validation import get_user_context

from clinicmgmt.classes.Entry import Entry
from clinicmgmt.classes.EntryAuthor import EntryAuthor
from clinicmgmt.classes.EntryDeletedAuthor import EntryDeletedAuthor

schedule = Blueprint("schedule", __name__)


@schedule.route('/', methods=['GET', 'POST'], endpoint="index")
@schedule.route('/printable', methods=['GET', 'POST'], endpoint="index_printable")
def index():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    timeframe = request.args.get('timeframe', "72hour")
    timeframe_str = LANG_STRINGS.OPERATIONS

    if request.method == 'POST':
        args_to_forward = request.form.to_dict()
    else:
        args_to_forward = request.args.to_dict()

    if timeframe == "search":
        args_to_forward["timeframe"] = "search"
    elif timeframe == "all":
        args_to_forward["timeframe"] = "all"

    author_id = request.form.get('author_id', request.args.get('author_id', ""))
    patient_name = request.form.get('patient_name', request.args.get('patient_name', ""))
    assigned_doctor_id = request.form.get('assigned_doctor_id', request.args.get('assigned_doctor_id', ""))
    assigned_doctor_name = request.form.get('assigned_doctor_name', request.args.get('assigned_doctor_name', ""))
    year_month = request.form.get('year_month', request.args.get('year_month', ""))
    html_timestamp = request.form.get('timestamp', request.args.get('timestamp', ""))
    type_of_surgery = request.form.get('type_of_surgery', request.args.get('type_of_surgery', ""))
    patient_birth_year = request.form.get('patient_birth_year', request.args.get('patient_birth_year', ""))
    patient_phone_number = request.form.get('patient_phone_number', request.args.get('patient_phone_number', ""))
    has_consultation_happened = request.form.get('has_consultation_happened',
                                                 request.args.get('has_consultation_happened', ""))

    base_query = ("SELECT id, author_id, last_edit_author_id, assigned_doctor_id, assigned_doctor_name, "
                  "patient_name, scheduled_timestamp, added_timestamp, last_edited_timestamp, type_of_surgery, "
                  "diagnosis, patient_birth_year, patient_phone_number, has_consultation_happened, "
                  "is_completed FROM patient_entries")

    where_conditions = []
    params = []

    if len(author_id) > 0:
        where_conditions.append("author_id = ?")
        params.append(author_id)

    if len(patient_name) > 0:
        where_conditions.append("patient_name LIKE ?")
        params.append("%" + patient_name + "%")

    if len(assigned_doctor_id) > 0:
        where_conditions.append("assigned_doctor_id = ?")
        params.append(assigned_doctor_id)

    if len(assigned_doctor_name) > 0:
        where_conditions.append("assigned_doctor_name LIKE ?")
        params.append("%" + assigned_doctor_name + "%")

    if len(type_of_surgery) > 0:
        where_conditions.append("type_of_surgery = ?")
        params.append(type_of_surgery)

    if len(patient_birth_year) > 0:
        where_conditions.append("patient_birth_year = ?")
        params.append(patient_birth_year)

    if len(patient_phone_number) > 0:
        where_conditions.append("patient_phone_number LIKE ?")
        params.append("%" + patient_phone_number + "%")

    if len(has_consultation_happened) > 0:
        where_conditions.append("has_consultation_happened = ?")
        params.append(has_consultation_happened)

    if timeframe == "72hour":
        time_now = time.time()

        where_conditions.append("scheduled_timestamp > ?")
        params.append((time_now - 86400))
        start_timestamp_obj = datetime.fromtimestamp((time_now - 86400), tz=website_context['timezone'])
        start_timestamp_str = start_timestamp_obj.strftime("%Y-%m-%d %H:%M")

        where_conditions.append("scheduled_timestamp < ?")
        params.append((time_now + 86400))
        end_timestamp_obj = datetime.fromtimestamp((time_now + 86400), tz=website_context['timezone'])
        end_timestamp_str = end_timestamp_obj.strftime("%Y-%m-%d %H:%M")

        timeframe_str = f"{start_timestamp_str} - {end_timestamp_str}"
    elif timeframe == "all":
        timeframe_str = LANG_STRINGS.ARCHIVE_AND_FUTURE
    else:
        timeframe_str = LANG_STRINGS.SEARCH_RESULTS

        if len(html_timestamp) > 0:
            where_conditions.append("scheduled_timestamp > ?")
            start_scheduled_timestamp_input_datetime = (datetime.strptime(html_timestamp + "T00:00:00" +
                                                                          website_context['timezone_str'],
                                                                          "%Y-%m-%dT%H:%M:%S%z"))
            start_scheduled_timestamp = int(start_scheduled_timestamp_input_datetime.timestamp())
            params.append(start_scheduled_timestamp - 1)

            where_conditions.append("scheduled_timestamp < ?")
            end_scheduled_timestamp_input_datetime = (datetime.strptime(html_timestamp + "T23:59:59" +
                                                                        website_context['timezone_str'],
                                                                        "%Y-%m-%dT%H:%M:%S%z"))
            end_scheduled_timestamp = int(end_scheduled_timestamp_input_datetime.timestamp())
            params.append(end_scheduled_timestamp + 1)

            timeframe_str = (f"{start_scheduled_timestamp_input_datetime.strftime('%Y-%m-%d %H:%M')} - "
                             f"{end_scheduled_timestamp_input_datetime.strftime('%Y-%m-%d %H:%M')}")

        if len(year_month) > 0:
            where_conditions.append("scheduled_timestamp > ?")
            start_scheduled_timestamp_input_datetime = (datetime.strptime(year_month + "-01T00:00:00" +
                                                                          website_context['timezone_str'],
                                                                          "%Y-%m-%dT%H:%M:%S%z"))
            start_scheduled_timestamp = int(start_scheduled_timestamp_input_datetime.timestamp())
            params.append(start_scheduled_timestamp - 1)

            where_conditions.append("scheduled_timestamp < ?")
            end_scheduled_timestamp_input_datetime = (datetime.strptime(year_month + "-28T23:59:59" +
                                                                        website_context['timezone_str'],
                                                                        "%Y-%m-%dT%H:%M:%S%z"))
            end_scheduled_timestamp = int(end_scheduled_timestamp_input_datetime.timestamp())

            if end_scheduled_timestamp_input_datetime.month in [1, 3, 5, 7, 8, 10, 12]:  # 31 day months
                append = 259200
            elif end_scheduled_timestamp_input_datetime.month in [4, 6, 9, 11]:  # 30 day months
                append = 172800
            elif end_scheduled_timestamp_input_datetime.month == 2:  # february :(
                year = end_scheduled_timestamp_input_datetime.year
                if (year % 400 == 0) or (year % 100 != 0) and (year % 4 == 0): # is leap year
                    append = 86400
                else:
                    append = 0
            else:
                append = 259200

            params.append(end_scheduled_timestamp + append + 1)
            timeframe_str = (f"{start_scheduled_timestamp_input_datetime.strftime('%Y-%m-%d %H:%M')} - "
                             f"{end_scheduled_timestamp_input_datetime.strftime('%Y-%m-%d %H:%M')}")
            # TODO: only 28 days show up, fix.

    if where_conditions:
        where_clause = " WHERE " + " AND ".join(where_conditions)
    else:
        where_clause = ""

    final_query = base_query + where_clause + " ORDER BY scheduled_timestamp ASC"

    print(final_query)
    entry_db_lookup = tuple(db_cursor.execute(final_query, params))

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

    if request.endpoint == "schedule.index_printable":
        print_timestamp_obj = datetime.fromtimestamp((time.time() + 86400), tz=website_context['timezone'])
        print_timestamp_str = print_timestamp_obj.strftime("%Y-%m-%d %H:%M")
        return make_response(
            render_template(
                "entry_listing_printable.html",
                WEBSITE_CONTEXT=website_context,
                USER_CONTEXT=user_context,
                ENTRIES=entries,
                TIMEFRAME_STR=timeframe_str,
                PRINT_TIMESTAMP_STR=print_timestamp_str,
                LANG_STRINGS=LANG_STRINGS
            )
        )
    else:
        return make_response(
            render_template(
                "entry_listing.html",
                WEBSITE_CONTEXT=website_context,
                USER_CONTEXT=user_context,
                ENTRIES=entries,
                TIMEFRAME_STR=timeframe_str,
                ARGS_TO_FORWARD=args_to_forward,
                LANG_STRINGS=LANG_STRINGS
            )
        )


@schedule.route('/entry_maker_form')
def entry_maker_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template(
        "entry_maker_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@schedule.route('/make_entry', methods=['POST'])
def make_entry():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    if request.method == 'POST':
        patient_name = request.form['patient_name']
        assigned_doctor_id = None
        assigned_doctor_name = request.form['assigned_doctor_name']
        html_timestamp = request.form['timestamp']
        type_of_surgery = request.form['type_of_surgery']
        diagnosis = request.form['diagnosis']
        patient_birth_year = request.form['patient_birth_year']
        patient_phone_number = request.form['patient_phone_number']
        has_consultation_happened = request.form['has_consultation_happened']

        if len(patient_birth_year) > 0:
            if not patient_birth_year.isdigit():
                return LANG_STRINGS.BIRTH_YEAR_MUST_BE_ONLY_4_DIGITS
        else:
            patient_birth_year = None

        scheduled_timestamp_input_datetime = datetime.strptime(html_timestamp + ":00" + website_context['timezone_str'], "%Y-%m-%dT%H:%M:%S%z")
        scheduled_timestamp = int(scheduled_timestamp_input_datetime.timestamp())

        entry_id = uuid.uuid4()

        db_cursor.execute("INSERT INTO patient_entries "
                          "(id, author_id, last_edit_author_id, assigned_doctor_id, assigned_doctor_name, "
                          "patient_name, scheduled_timestamp, added_timestamp, last_edited_timestamp, "
                          "type_of_surgery, diagnosis, patient_birth_year, patient_phone_number, "
                          "has_consultation_happened, is_completed) "
                          "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                          [str(entry_id), user_context.id, user_context.id, assigned_doctor_id, assigned_doctor_name,
                           patient_name, int(scheduled_timestamp), int(time.time()), int(time.time()), type_of_surgery,
                           diagnosis, patient_birth_year, patient_phone_number, int(has_consultation_happened), 0])
        db_connection.commit()

        resp = make_response(redirect(url_for("schedule.entry_view", entry_id=entry_id)))

        return resp


@schedule.route('/entry_view/<entry_id>')
def entry_view(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    entry_db_lookup = tuple(
        db_cursor.execute("SELECT id, author_id, last_edit_author_id, assigned_doctor_id, assigned_doctor_name, "
                          "patient_name, scheduled_timestamp, added_timestamp, last_edited_timestamp, type_of_surgery, "
                          "diagnosis, patient_birth_year, patient_phone_number, has_consultation_happened, "
                          "is_completed FROM patient_entries WHERE id = ? ", [entry_id]))
    if not entry_db_lookup:
        return LANG_STRINGS.RECORD_NOT_FOUND_PROBABLY_DELETED

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

            approval_timestamp_tmp = datetime.fromtimestamp(self.approval_timestamp, tz=website_context['timezone'])
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
            entry.approvers.append(Approver([entry_approver_db[0], LANG_STRINGS.DELETED_USER], entry_approvals[1]))

        if entry_approvals[0] == user_context.id:
            entry.current_user_has_approved = 1

    return render_template(
        "entry_view.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        ENTRY=entry,
        LANG_STRINGS=LANG_STRINGS
    )


@schedule.route('/entry_edit_form/<entry_id>')
def entry_edit_form(entry_id):
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    entry_db_lookup = tuple(
        db_cursor.execute("SELECT id, author_id, last_edit_author_id, assigned_doctor_id, assigned_doctor_name, "
                          "patient_name, scheduled_timestamp, added_timestamp, last_edited_timestamp, type_of_surgery, "
                          "diagnosis, patient_birth_year, patient_phone_number, has_consultation_happened, "
                          "is_completed FROM patient_entries WHERE id = ?", [entry_id]))

    if not entry_db_lookup:
        return LANG_STRINGS.RECORD_NOT_FOUND_PROBABLY_DELETED

    entry = Entry(entry_db_lookup[0])

    return render_template(
        "entry_edit_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        ENTRY=entry,
        LANG_STRINGS=LANG_STRINGS
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
        assigned_doctor_id = None
        assigned_doctor_name = request.form['assigned_doctor_name']
        timestamp = request.form['timestamp']
        type_of_surgery = request.form['type_of_surgery']
        diagnosis = request.form['diagnosis']
        patient_birth_year = request.form['patient_birth_year']
        patient_phone_number = request.form['patient_phone_number']
        has_consultation_happened = request.form['has_consultation_happened']
        is_completed = request.form['is_completed']

        if len(patient_birth_year) > 0:
            if not patient_birth_year.isdigit():
                return LANG_STRINGS.BIRTH_YEAR_MUST_BE_ONLY_4_DIGITS
        else:
            patient_birth_year = None

        scheduled_timestamp_input_datetime = datetime.strptime(timestamp + ":00" + website_context['timezone_str'], "%Y-%m-%dT%H:%M:%S%z")
        scheduled_timestamp = int(scheduled_timestamp_input_datetime.timestamp())

        db_cursor.execute("UPDATE patient_entries "
                          "SET last_edit_author_id = ?, assigned_doctor_id = ?, assigned_doctor_name = ?, "
                          "patient_name = ?, scheduled_timestamp = ?, last_edited_timestamp = ?, type_of_surgery = ?, "
                          "diagnosis = ?, patient_birth_year = ?, patient_phone_number = ?, "
                          "has_consultation_happened = ?, is_completed = ? WHERE id = ?",
                          [user_context.id, assigned_doctor_id, assigned_doctor_name, patient_name,
                           scheduled_timestamp, int(time.time()), type_of_surgery,
                           diagnosis, patient_birth_year, patient_phone_number,
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
        return LANG_STRINGS.YOU_DO_NOT_HAVE_PERMISSIONS_TO_GIVE_APPROVALS

    already_approved = tuple(db_cursor.execute("SELECT patient_id FROM patient_doctor_approvals "
                                               "WHERE patient_id = ? AND approver_author_id = ?",
                                               [str(entry_id), str(user_context.id)]))

    if already_approved:
        return LANG_STRINGS.YOU_ALREADY_APPROVED_THIS_PATIENT

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
        return LANG_STRINGS.YOU_DO_NOT_HAVE_PERMISSIONS_TO_DELETE_APPROVALS

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

    return render_template(
        "search_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )


@schedule.route('/calendar_form')
def calendar_form():
    user_context = get_user_context()
    if not user_context:
        return redirect(url_for("user_management.login_form"))

    return render_template(
        "calendar_form.html",
        WEBSITE_CONTEXT=website_context,
        USER_CONTEXT=user_context,
        LANG_STRINGS=LANG_STRINGS
    )
