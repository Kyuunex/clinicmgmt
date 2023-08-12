from datetime import datetime

from clinicmgmt.reusables.context import website_context


class Entry:
    def __init__(self, entry_db_lookup):
        self.entry_id = entry_db_lookup[0]
        self.author_id = entry_db_lookup[1]
        self.last_edit_author_id = entry_db_lookup[2]
        self.assigned_doctor_id = entry_db_lookup[3]
        self.assigned_doctor_name = entry_db_lookup[4]
        self.patient_name = entry_db_lookup[5]
        self.scheduled_timestamp = entry_db_lookup[6]
        self.added_timestamp = entry_db_lookup[7]
        self.last_edited_timestamp = entry_db_lookup[8]
        self.type_of_surgery = entry_db_lookup[9]
        self.diagnosis = entry_db_lookup[10]
        self.patient_birth_year = entry_db_lookup[11]
        self.patient_phone_number = entry_db_lookup[12]
        self.has_consultation_happened = entry_db_lookup[13]
        self.is_completed = entry_db_lookup[14]

        scheduled_timestamp_tmp = datetime.fromtimestamp(self.scheduled_timestamp, tz=website_context['timezone'])
        self.scheduled_timestamp_str = scheduled_timestamp_tmp.strftime("%Y-%m-%d %H:%M")
        self.scheduled_timestamp_html = scheduled_timestamp_tmp.strftime("%Y-%m-%dT%H:%M")

        last_edited_timestamp_tmp = datetime.fromtimestamp(self.last_edited_timestamp, tz=website_context['timezone'])
        self.last_edited_timestamp_str = last_edited_timestamp_tmp.strftime("%Y-%m-%d %H:%M")

        added_timestamp_tmp = datetime.fromtimestamp(self.added_timestamp, tz=website_context['timezone'])
        self.added_timestamp_str = added_timestamp_tmp.strftime("%Y-%m-%d %H:%M")
