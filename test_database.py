from database.db import init_db
from config import Config

def test_database_init():
    init_db()
    assert Config.DATABASE_PATH.parent.exists()
