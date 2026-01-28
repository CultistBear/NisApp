import logging
from constants import DATABASE_URL, DATABASE_NAME, DB_USERNAME, DB_PASSWORD, DB_HOST, DB_PORT, IS_PRODUCTION

if IS_PRODUCTION:
    import psycopg2
    import psycopg2.extras
else:
    import pymysql

class DB:
    def __init__(self):
        logging.info("Initializing database connection")
        self.connect()

    def connect(self):
        if IS_PRODUCTION:
            if DATABASE_URL:
                self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=psycopg2.extras.RealDictCursor)
            else:
                self.conn = psycopg2.connect(
                    user=DB_USERNAME,
                    password=DB_PASSWORD,
                    database=DATABASE_NAME,
                    host=DB_HOST,
                    port=DB_PORT,
                    cursor_factory=psycopg2.extras.RealDictCursor
                )
            self.conn.autocommit = False
        else:
            self.conn = pymysql.connect(
                user=DB_USERNAME,
                password=DB_PASSWORD,
                database=DATABASE_NAME,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False 
            )

    def select(self, sql, params=None):
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchall()

    def execute(self, sql, params=None):
        with self.conn.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.rowcount

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()

