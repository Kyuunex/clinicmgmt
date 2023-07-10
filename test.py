#!/usr/bin/env python3
import os

os.environ["CLINICMGMT_SQLITE_FILE"] = os.path.expanduser("~") + "/Documents/clinicmgmt.sqlite3"

from clinicmgmt import app as application

application.run(
    host='127.0.0.1',
    port=8077,
    debug=True
)
