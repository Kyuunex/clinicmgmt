class InviteAuthor:
    def __init__(self, invite_author_db_lookup):
        self.id = invite_author_db_lookup[0]
        self.email = invite_author_db_lookup[1]
        self.display_name = invite_author_db_lookup[2]
        self.is_administrator = invite_author_db_lookup[3]
        self.is_approver = invite_author_db_lookup[4]
