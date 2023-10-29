# Installation for production use (Non-Docker Instructions)
Type the following in the command line to install the master branch of this software as a pip package.
Important, You need `git` and Python 3.11+ installed beforehand.

```bash
python3 -m pip install git+https://github.com/Kyuunex/clinicmgmt.git@master
```  

To install a specific version, replace `master` at the end with the version you want to install from releases.  
Additionally, every release has a command in its description for easy installation of that specific version.  
But for security reasons, using the latest version is always recommended.  
To update from an older version, simply append `--upgrade` to this command.

### Example Apache 2 configuration
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

### Example wsgi file:
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