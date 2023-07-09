class EntryDeletedAuthor:
    def __init__(self, author_id):
        self.id = author_id
        self.email = author_id + "@deleted_account"
        self.display_name = "Deleted User"
        self.is_administrator = 0
        self.is_approver = 0
