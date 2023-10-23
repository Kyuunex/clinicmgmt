from datetime import datetime

from clinicmgmt.reusables.context import website_context


class Invite:
    def __init__(self, invite_db_lookup):
        self.invite_code = invite_db_lookup[0]
        self.invitee_email = invite_db_lookup[1]
        self.inviter_id = invite_db_lookup[2]
        self.generation_timestamp = invite_db_lookup[3]
        self.expiry_timestamp = invite_db_lookup[4]

        generation_timestamp_tmp = datetime.fromtimestamp(self.generation_timestamp, tz=website_context['timezone'])
        self.generation_timestamp_str = generation_timestamp_tmp.strftime("%Y-%m-%d %H:%M")

        expiry_timestamp_tmp = datetime.fromtimestamp(self.expiry_timestamp, tz=website_context['timezone'])
        self.expiry_timestamp_str = expiry_timestamp_tmp.strftime("%Y-%m-%d %H:%M")

