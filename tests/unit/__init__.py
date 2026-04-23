import os
import unittest

import giraffe
import sqlalchemy


class FreshModelTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        """"""

        # build connection url
        port = os.environ.get("DB_PORT") or None
        if port is not None:
            port = int(port)
        url = sqlalchemy.URL.create(
            drivername=os.environ.get("DB_DRIVER", "sqlite"),
            username=os.environ.get("DB_USER"),
            password=os.environ.get("DB_PASSWORD"),
            host=os.environ.get("DB_HOST"),
            port=port,
            database=os.environ.get("DB_NAME")
        )

        # build database
        self.engine = sqlalchemy.create_engine(url, pool_pre_ping=True)
        self.db = giraffe.Database(self.engine)

        # migrate and clean
        self.db.load_schema()
        self.db.connection.execute(sqlalchemy.text("DELETE FROM cycle_edge"))
        self.db.connection.execute(sqlalchemy.text("DELETE FROM cycle"))
        self.db.connection.execute(sqlalchemy.text("DELETE FROM edge"))
        self.db.connection.execute(sqlalchemy.text("DELETE FROM vertex"))
        self.db.connection.execute(sqlalchemy.text("DELETE FROM graph"))


    def tearDown(self):
        """"""
        self.db.close()
        self.engine.dispose()
        self.engine = None
        self.db = None
