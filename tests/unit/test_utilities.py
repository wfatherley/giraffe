import inspect
import unittest

import giraffe


class TestColor(unittest.TestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("Color", dir(giraffe))

    def test_has_white_as_zero(self):
        """"""
        self.assertEqual(0, giraffe.Color.WHITE)

    def test_has_gray_as_one(self):
        """"""
        self.assertEqual(1, giraffe.Color.GRAY)

    def test_has_black_as_two(self):
        """"""
        self.assertEqual(2, giraffe.Color.BLACK)
