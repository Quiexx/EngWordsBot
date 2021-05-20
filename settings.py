import os
import re

DB_URL_ITEMS = re.compile("\w*:\/\/(\w+):(\w+)@([\w.-]+):\d*\/(\w*)")

# VK group id
GROUP_ID = os.environ.get("GROUP_ID")

# VK group token
TOKEN = os.environ.get("TOKEN")

#Database URL
DB_URL = os.environ.get("JAWSDB_URL")

# Database configuration
user = DB_URL_ITEMS.match(DB_URL)[1]
password = DB_URL_ITEMS.match(DB_URL)[2]
host = DB_URL_ITEMS.match(DB_URL)[3]
db_name = DB_URL_ITEMS.match(DB_URL)[4]

DB_CONFIG = dict(provider='mysql', host=host, user=user, passwd=password, db=db_name)
