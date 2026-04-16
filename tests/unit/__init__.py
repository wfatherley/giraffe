import sqlite3
import unittest

import giraffe
import sqlalchemy


class FreshModelTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        """"""
        self.engine = sqlalchemy.create_engine("sqlite:///:memory:")
        self.db = giraffe.Database(self.engine)
        self.db.load_schema()

    def tearDown(self):
        """"""
        self.db.close()
        self.engine.dispose()
        self.engine = None
        self.db = None
