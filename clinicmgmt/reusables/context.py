import os
import sqlite3
from datetime import timedelta, timezone
import locale
from clinicmgmt.reusables.convert_times import str_to_seconds

if not os.environ.get('CLINICMGMT_SQLITE_FILE'):
    print("This app uses an sqlite3 database. "
          "You need to EXPORT a location of the database file to CLINICMGMT_SQLITE_FILE")
    raise SystemExit

SQLITE_FILE = os.environ.get('CLINICMGMT_SQLITE_FILE')

db_connection = sqlite3.connect(SQLITE_FILE, check_same_thread=False)
db_cursor = db_connection.cursor()
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "users" (
            "id"    TEXT NOT NULL UNIQUE,
            "email"    TEXT NOT NULL UNIQUE,
            "display_name"    TEXT NOT NULL,
            "is_administrator"    INTEGER NOT NULL,
            "is_approver"    INTEGER NOT NULL
        )
""")
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "session_tokens" (
            "user_id"    TEXT NOT NULL,
            "token_id"    TEXT NOT NULL,
            "token"    TEXT NOT NULL,
            "timestamp"    INTEGER NOT NULL,
            "expiry_timestamp"    INTEGER NOT NULL,
            "user_agent"    TEXT NOT NULL,
            "ip_address"    INTEGER NOT NULL,
            "is_ipv6"    INTEGER NOT NULL
        )
""")
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "user_passwords" (
            "user_id"    TEXT NOT NULL UNIQUE,
            "password_hash"    TEXT NOT NULL,
            "password_salt"    TEXT NOT NULL
        )
""")
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "patient_entries" (
            "id"    TEXT NOT NULL,
            "author_id"    TEXT NOT NULL,
            "last_edit_author_id"    TEXT NOT NULL,
            "assigned_doctor_id"    TEXT,
            "assigned_doctor_name"    TEXT,
            "patient_name"    TEXT NOT NULL,
            "scheduled_timestamp"    INTEGER NOT NULL,
            "added_timestamp"    INTEGER NOT NULL,
            "last_edited_timestamp"    INTEGER,
            "type_of_surgery"    TEXT NOT NULL,
            "diagnosis"    TEXT NOT NULL,
            "patient_birth_year"    INTEGER,
            "patient_phone_number"    TEXT,
            "has_consultation_happened"    INTEGER NOT NULL,
            "is_completed"    INTEGER NOT NULL
        )
""")
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "invite_codes" (
            "invite_code"    TEXT NOT NULL,
            "invitee_email"    TEXT NOT NULL,
            "inviter_id"    TEXT NOT NULL,
            "generation_timestamp"    INTEGER NOT NULL,
            "expiry_timestamp"    INTEGER NOT NULL
        )
""")
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "patient_doctor_approvals" (
            "patient_id"    TEXT NOT NULL,
            "approver_author_id"    TEXT NOT NULL,
            "approval_timestamp"    INTEGER NOT NULL
        )
""")
db_cursor.execute("""
        CREATE TABLE IF NOT EXISTS "app_configuration" (
            "setting"    TEXT NOT NULL,
            "value"    TEXT NOT NULL
        )
""")
db_connection.commit()

website_context = {}

user_context_list = tuple(db_cursor.execute(
    "SELECT value FROM app_configuration WHERE setting = ?", ["title"])
)

language_to_use_db = tuple(db_cursor.execute(
    "SELECT value FROM app_configuration WHERE setting = ?", ["language"])
)

timezone_str_db = tuple(db_cursor.execute(
    "SELECT value FROM app_configuration WHERE setting = ?", ["timezone_str"])
)

if language_to_use_db:
    language_to_use = language_to_use_db[0][0]
else:
    language_to_use = "en_US"

if timezone_str_db:
    timezone_str = timezone_str_db[0][0]
else:
    timezone_str = "+00:00"

if language_to_use == "ka_GE":
    try:
        locale.setlocale(locale.LC_TIME, 'ka_GE.utf8')
    except locale.Error:
        print("ქართული ენის locale არ არის გენერირებული ამ სისტემაზე! ინგლისური იქნება გამოყენებული")
    from clinicmgmt.localization import ka_GE as LANG_STRINGS
elif language_to_use == "en_US":
    from clinicmgmt.localization import en_US as LANG_STRINGS
else:
    from clinicmgmt.localization import en_US as LANG_STRINGS

if user_context_list:
    website_context["title"] = user_context_list[0][0]
else:
    website_context["title"] = LANG_STRINGS.SCHEDULE

website_context["timezone_str"] = timezone_str
website_context["timezone"] = timezone(timedelta(seconds=str_to_seconds(timezone_str)))
