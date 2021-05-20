from pony.orm import Database, Required, Json, Optional

from settings import DB_CONFIG

db = Database()
db.bind(**DB_CONFIG)


class Words(db.Entity):
    word = Required(str)
    using_count = Required(int)


class UserState(db.Entity):
    user_id = Required(str, unique=True)
    dictionary = Required(Json)
    last_word = Optional(str)
    test_list = Optional(Json)
    bot_state_name = Required(str)


db.generate_mapping(create_tables=True)
