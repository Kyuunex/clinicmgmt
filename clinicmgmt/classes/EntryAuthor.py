class EntryAuthor:
    def __init__(self, entry_author_db_lookup):
        self.id = entry_author_db_lookup[0]
        self.email = entry_author_db_lookup[1]
        self.display_name = entry_author_db_lookup[2]
        self.is_administrator = entry_author_db_lookup[3]
        self.is_approver = entry_author_db_lookup[4]
