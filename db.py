from flask import g
from databaseManagement import DB

def get_db():
    if "db" not in g:
        g.db = DB()
    return g.db

def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()
