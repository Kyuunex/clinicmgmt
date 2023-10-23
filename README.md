# clinicmgmt
Internal clinic management web-portal, made in Flask.
კლინიკის მენჯმენტის ვებ-პორტალი

# Georgian only
This software was written for a clinic in Georgia and is only in Georgian Language. 
Multilingual update will come later.

### Installation for prod
Install this as a pip package with this command `python3 -m pip install . --upgrade`.
Then make an apache conf that looks something like this
```bash
<IfModule mod_ssl.c>
    <VirtualHost *:443>
        ServerName management.internal-domain.com
        ServerAdmin webmaster@your-domain.com

        WSGIScriptAlias / /var/www/clinicmgmt/clinicmgmtloader.wsgi

        SSLEngine on

        SSLCertificateFile /root/ssl/management.internal-domain.com.pem
        SSLCertificateKeyFile /root/ssl/management.internal-domain.com.key

        LogLevel warn
        ErrorLog ${APACHE_LOG_DIR}/error.log
        CustomLog ${APACHE_LOG_DIR}/access.log combined
    </VirtualHost>
</IfModule>
```
And make a wsgi file that looks something like this
```python
#!/usr/bin/env python3

import os
import sys
import logging

logging.basicConfig(stream=sys.stderr)
os.environ["CLINICMGMT_SQLITE_FILE"] = "/var/www/clinicmgmt_database/clinicmgmt.sqlite3"
# the path above has to be writable

from clinicmgmt import app as application

```
