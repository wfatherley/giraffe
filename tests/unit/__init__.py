import sqlite3
import unittest

import giraffe


class FreshModelTestCase(unittest.TestCase):
    """"""

    def setUp(self):
        """"""

        # a default connection
        self.con = sqlite3.connect(":memory:", autocommit=False)
        for table_definition in giraffe.Database.model.split(";"):
            _ = self.con.execute(table_definition.strip())

    def tearDown(self):
        """"""
        self.con.close()
