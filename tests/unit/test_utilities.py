import collections
import inspect
import sqlite3
import unittest

import giraffe


class TestColor(unittest.TestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("Color", dir(giraffe))

    def test_has_white_as_zero(self):
        """"""
        self.assertEqual(0, giraffe.Color.white)

    def test_has_gray_as_one(self):
        """"""
        self.assertEqual(1, giraffe.Color.gray)

    def test_has_black_as_two(self):
        """"""
        self.assertEqual(2, giraffe.Color.black)


class TestEdgeODictFactory(unittest.TestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("edge_odict_factory", dir(giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.edge_odict_factory))

    def test_signature_unchanged(self):
        """"""
        s = inspect.signature(giraffe.edge_odict_factory)
        self.assertEqual(len(s.parameters), 0)

    def test_returns_ordered_dict(self):
        """"""
        self.assertIsInstance(giraffe.edge_odict_factory(), collections.OrderedDict)


class TestVertexODictFactory(unittest.TestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("vertex_odict_factory", dir(giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.vertex_odict_factory))

    def test_signature_unchanged(self):
        """"""
        s = inspect.signature(giraffe.vertex_odict_factory)
        self.assertEqual(len(s.parameters), 0)

    def test_returns_ordered_dict(self):
        """"""
        self.assertIsInstance(
            giraffe.vertex_odict_factory(), collections.OrderedDict
        )
