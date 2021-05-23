from pony.orm import Database, Required, Json, Optional, IntArray, StrArray

from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class Words(db.Entity):
    word = Required(str)
    using_count = Required(int)


class UserState(db.Entity):
    user_id = Required(str, unique=True)
    dictionary = Required(Json)
    buffer = Required(Json)
    bot_state_name = Required(str)


db.generate_mapping(create_tables=True)
