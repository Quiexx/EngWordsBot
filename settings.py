import os

# VK group id
GROUP_ID = os.environ.get("GROUP_ID")

# VK group token
TOKEN = os.environ.get("TOKEN")

# Database configuration
DB_CONFIG = dict(provider='sqlite', filename='EngWords_database.sqlite', create_db=True)


