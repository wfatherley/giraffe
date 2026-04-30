import functools
import inspect
import itertools
import math

import giraffe
import sqlalchemy

from . import FreshModelTestCase


class TestEBFSearch(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("ebf_search", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.ebf_search))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.ebf_search)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        start_edge_id = s.parameters["start_edge_id"]
        self.assertEqual(start_edge_id.default, start_edge_id.empty)
        self.assertEqual(start_edge_id.kind, start_edge_id.POSITIONAL_OR_KEYWORD)

    def test_raise_on_immutable_graph(self):
        """"""
        self.db.create_graph("test", 1)

        for i in range(1, 5):
            for c in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, c)
                self.db.connection.execute(sqlalchemy.text("UPDATE graph SET mode = :mode"), {"mode": flags})
                with self.assertRaises(Exception):
                    self.db.ebf_search("x")

    def test_raise_with_bad_start_vertex(self):
        """"""
        self.db.create_graph("test", 1)
        with self.assertRaises(Exception):
            self.db.ebf_search("test", 2)

    def test_handle_cormen_etal_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(8)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[4]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[5], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7]},
        )
        self.db.ebf_search("test", 1)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT id, predecessor FROM edge ORDER BY id")
            ).fetchall(),
            [
                (0, 1),
                (1, None),
                (2, 0),
                (3, 4),
                (4, 2),
                (5, None),
                (6, None),
                (7, None),
                (8, 2),
                (9, 8)
            ]
        )

    def test_handle_weird_peterson(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(10)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[4]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[0]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[8]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[9]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[8]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[9]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5]},
        )
        self.db.ebf_search("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT id, predecessor FROM edge ORDER BY id")
            ).fetchall(),
            [
                (0, None),
                (1, 0),
                (2, 1),
                (3, None),
                (4, 0),
                (5, 0),
                (6, None),
                (7, None),
                (8, None),
                (9, 4),
                (10, 0),
                (11, 0),
                (12, 1),
                (13, None),
                (14, None)
            ],
        )

    def test_handle_peterson(self):
        """"""
        self.db.create_peterson("test")
        self.db.ebf_search("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT id, predecessor FROM edge ORDER BY id")
            ).fetchall(),
            [
                (0, None),
                (1, 0),
                (2, 1),
                (3, None),
                (4, 0),
                (5, 0),
                (6, 0),
                (7, 1),
                (8, 2),
                (9, 4),
                (10, None),
                (11, None),
                (12, None),
                (13, None),
                (14, None)
            ],
        )

    def test_handle_frucht(self):
        """"""
        self.db.create_frucht("test")
        self.db.ebf_search("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT id, predecessor FROM edge ORDER BY id")
            ).fetchall(),
            [
                (0, None),
                (1, 0),
                (2, 1),
                (3, 2),
                (4, None),
                (5, 6),
                (6, 0),
                (7, 0),
                (8, 0),
                (9, None),
                (10, 2),
                (11, None),
                (12, None),
                (13, 6),
                (14, None),
                (15, 7),
                (16, None),
                (17, None)
            ]
        )


class TestVBFSearch(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("vbf_search", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.vbf_search))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.vbf_search)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        start_vertex_id = s.parameters["start_vertex_id"]
        self.assertEqual(start_vertex_id.default, start_vertex_id.empty)
        self.assertEqual(start_vertex_id.kind, start_vertex_id.POSITIONAL_OR_KEYWORD)

    def test_raise_on_immutable_graph(self):
        """"""
        self.db.create_graph("test", 1)

        for i in range(1, 5):
            for c in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, c)
                self.db.connection.execute(sqlalchemy.text("UPDATE graph SET mode = :flags"), {"flags": flags})
                self.db.connection.commit()
                with self.assertRaises(Exception):
                    self.db.vbf_search("x")

    def test_raise_with_bad_start_vertex(self):
        """"""
        self.db.create_graph("test", 1)
        with self.assertRaises(Exception):
            self.db.vbf_search("test", 2)

    def test_handle_cormen_etal_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(8)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[4]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[5], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7]},
        )
        self.db.vbf_search("test", 1)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, color, pushed, predecessor, bf_distance
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 2, 2, 1, 1),
                (1, 2, 1, None, 0),
                (2, 2, 5, 5, 2),
                (3, 2, 7, 2, 3),
                (4, 2, 4, 0, 2),
                (5, 2, 3, 1, 1),
                (6, 2, 6, 5, 2),
                (7, 2, 8, 6, 3)
            ],
        )

    def test_handle_weird_peterson(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(10)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[4]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[0]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[8]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[9]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[8]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[9]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5]},
        )
        self.db.vbf_search("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, color, pushed,predecessor, bf_distance
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 2, 1, None, 0),
                (1, 2, 2, 0, 1),
                (2, 2, 6, 1, 2),
                (3, 2, 8, 4, 2),
                (4, 2, 3, 0, 1),
                (5, 2, 4, 0, 1),
                (6, 2, 5, 0, 1),
                (7, 2, 7, 1, 2),
                (8, 2, 10, 2, 3),
                (9, 2, 9, 4, 2)
            ],
        )

    def test_handle_peterson(self):
        """"""
        self.db.create_peterson("test")
        self.db.vbf_search("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 2, None, 0),
                (1, 2, 0, 1),
                (2, 2, 1, 2),
                (3, 2, 4, 2),
                (4, 2, 0, 1),
                (5, 2, 0, 1),
                (6, 2, 1, 2),
                (7, 2, 2, 3),
                (8, 2, 3, 3),
                (9, 2, 4, 2),
            ],
        )

    def test_handle_frucht(self):
        """"""
        self.db.create_frucht("test")
        self.db.vbf_search("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 2, None, 0),
                (1, 2, 0, 1),
                (2, 2, 1, 2),
                (3, 2, 0, 1),
                (4, 2, 3, 2),
                (5, 2, 1, 2),
                (6, 2, 4, 3),
                (7, 2, 5, 3),
                (8, 2, 11, 3),
                (9, 2, 10, 2),
                (10, 2, 0, 1),
                (11, 2, 10, 2),
            ],
        )


class TestMinimumSpanningTree(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("minimum_spanning_tree", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.minimum_spanning_tree))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.minimum_spanning_tree)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        start_edge_id = s.parameters["start_vertex_id"]
        self.assertEqual(start_edge_id.default, start_edge_id.empty)
        self.assertEqual(start_edge_id.kind, start_edge_id.POSITIONAL_OR_KEYWORD)

    def test_handle_cormen_et_al_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(9)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "weight": 4},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2], "weight": 8},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3], "weight": 7},
            {"parent_vertex_id": _[3], "child_vertex_id": _[4], "weight": 9},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5], "weight": 10},
            {"parent_vertex_id": _[5], "child_vertex_id": _[6], "weight": 2},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7], "weight": 1},
            {"parent_vertex_id": _[7], "child_vertex_id": _[0], "weight": 8},
            {"parent_vertex_id": _[7], "child_vertex_id": _[1], "weight": 11},
            {"parent_vertex_id": _[7], "child_vertex_id": _[8], "weight": 7},
            {"parent_vertex_id": _[8], "child_vertex_id": _[2], "weight": 2},
            {"parent_vertex_id": _[6], "child_vertex_id": _[8], "weight": 6},
            {"parent_vertex_id": _[2], "child_vertex_id": _[5], "weight": 4},
            {"parent_vertex_id": _[3], "child_vertex_id": _[5], "weight": 14}
        )
        self.db.minimum_spanning_tree("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, predecessor
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, None),
                (1, 0),
                (2, 1),
                (3, 2),
                (4, 3),
                (5, 2),
                (6, 5),
                (7, 6),
                (8, 2)
            ]
        )

    def test_handle_modified_cormen_et_al_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(9)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "weight": 4},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2], "weight": 8},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3], "weight": 7},
            {"parent_vertex_id": _[3], "child_vertex_id": _[4], "weight": 9},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5], "weight": 10},
            {"parent_vertex_id": _[5], "child_vertex_id": _[6], "weight": 2},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7], "weight": 8},
            {"parent_vertex_id": _[7], "child_vertex_id": _[0], "weight": 1},
            {"parent_vertex_id": _[7], "child_vertex_id": _[1], "weight": 11},
            {"parent_vertex_id": _[7], "child_vertex_id": _[8], "weight": 7},
            {"parent_vertex_id": _[8], "child_vertex_id": _[2], "weight": 2},
            {"parent_vertex_id": _[6], "child_vertex_id": _[8], "weight": 6},
            {"parent_vertex_id": _[2], "child_vertex_id": _[5], "weight": 4},
            {"parent_vertex_id": _[3], "child_vertex_id": _[5], "weight": 14}
        )
        self.db.minimum_spanning_tree("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, predecessor
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, None),
                (1, 0),
                (2, 8),
                (3, 2),
                (4, 3),
                (5, 2),
                (6, 5),
                (7, 0),
                (8, 7)
            ]
        )

    def test_handle_weird_peterson(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(10)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "weight": 1},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2], "weight": 5},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3], "weight": 3},
            {"parent_vertex_id": _[3], "child_vertex_id": _[4], "weight": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[0], "weight": 5},
            {"parent_vertex_id": _[0], "child_vertex_id": _[5], "weight": 5},
            {"parent_vertex_id": _[1], "child_vertex_id": _[6], "weight": 3},
            {"parent_vertex_id": _[2], "child_vertex_id": _[7], "weight": 5},
            {"parent_vertex_id": _[3], "child_vertex_id": _[8], "weight": 12},
            {"parent_vertex_id": _[4], "child_vertex_id": _[9], "weight": 1},
            {"parent_vertex_id": _[0], "child_vertex_id": _[6], "weight": 2},
            {"parent_vertex_id": _[1], "child_vertex_id": _[7], "weight": 1},
            {"parent_vertex_id": _[2], "child_vertex_id": _[8], "weight": 6},
            {"parent_vertex_id": _[3], "child_vertex_id": _[9], "weight": 9},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5], "weight": 2},
        )
        self.db.minimum_spanning_tree("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT id, predecessor FROM vertex ORDER BY id")
            ).fetchall(),
            [
                (0, None),
                (1, 0),
                (2, 1),
                (3, 2),
                (4, 0),
                (5, 4),
                (6, 0),
                (7, 1),
                (8, 2),
                (9, 4)
            ],
        )


class TestSingleSourceShortestPath(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("single_source_shortest_path", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.single_source_shortest_path))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.single_source_shortest_path)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        start_edge_id = s.parameters["start_vertex_id"]
        self.assertEqual(start_edge_id.default, start_edge_id.empty)
        self.assertEqual(start_edge_id.kind, start_edge_id.POSITIONAL_OR_KEYWORD)

    def test_handle_cormen_et_al_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(5)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "weight": 10},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2], "weight": 1},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3], "weight": 4},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2], "weight": 6},
            {"parent_vertex_id": _[4], "child_vertex_id": _[3], "weight": 2},
            {"parent_vertex_id": _[0], "child_vertex_id": _[4], "weight": 5},
            {"parent_vertex_id": _[3], "child_vertex_id": _[0], "weight": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[2], "weight": 9},
            {"parent_vertex_id": _[4], "child_vertex_id": _[1], "weight": 3},
            {"parent_vertex_id": _[1], "child_vertex_id": _[4], "weight": 2}
        )
        self.db.single_source_shortest_path("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, predecessor, sp_estimate
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, None, 0),
                (1, 4, 8),
                (2, 1, 9),
                (3, 4, 7),
                (4, 0, 5)
            ]
        )

    def test_handle_modifed_cormen_et_al_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(5)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "weight": 10},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2], "weight": 1},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3], "weight": 4},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2], "weight": 6},
            {"parent_vertex_id": _[4], "child_vertex_id": _[3], "weight": 20},
            {"parent_vertex_id": _[0], "child_vertex_id": _[4], "weight": 5},
            {"parent_vertex_id": _[3], "child_vertex_id": _[0], "weight": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[2], "weight": 9},
            {"parent_vertex_id": _[4], "child_vertex_id": _[1], "weight": 3},
            {"parent_vertex_id": _[1], "child_vertex_id": _[4], "weight": 2}
        )
        self.db.single_source_shortest_path("test", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, predecessor, sp_estimate
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, None, 0),
                (1, 4, 8),
                (2, 1, 9),
                (3, 2, 13),
                (4, 0, 5)
            ]
        )


class TestMaximumFlow(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("maximum_flow", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.maximum_flow))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.maximum_flow)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 4)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        source_vertex_id = s.parameters["source_vertex_id"]
        self.assertEqual(source_vertex_id.default, source_vertex_id.empty)
        self.assertEqual(source_vertex_id.kind, source_vertex_id.POSITIONAL_OR_KEYWORD)

        sink_vertex_id = s.parameters["sink_vertex_id"]
        self.assertEqual(sink_vertex_id.default, sink_vertex_id.empty)
        self.assertEqual(sink_vertex_id.kind, sink_vertex_id.POSITIONAL_OR_KEYWORD)

    def test_handle_cormen_et_al_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(6)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "mf_capacity": 16},
            {"parent_vertex_id": _[0], "child_vertex_id": _[2], "mf_capacity": 13},
            {"parent_vertex_id": _[2], "child_vertex_id": _[1], "mf_capacity": 4},
            {"parent_vertex_id": _[1], "child_vertex_id": _[3], "mf_capacity": 12},
            {"parent_vertex_id": _[2], "child_vertex_id": _[4], "mf_capacity": 14},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2], "mf_capacity": 9},
            {"parent_vertex_id": _[3], "child_vertex_id": _[5], "mf_capacity": 20},
            {"parent_vertex_id": _[4], "child_vertex_id": _[3], "mf_capacity": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5], "mf_capacity": 4}
        )
        self.db.maximum_flow("test", 0, 5)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, mf_flow
                FROM edge
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 12),
                (1, 11),
                (2, 0),
                (3, 12),
                (4, 11),
                (5, 0),
                (6, 19),
                (7, 7),
                (8, 4)
            ]
        )

    def test_handle_cormen_et_al_antiparallel_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(6)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "mf_capacity": 16},
            {"parent_vertex_id": _[0], "child_vertex_id": _[2], "mf_capacity": 13},
            {"parent_vertex_id": _[2], "child_vertex_id": _[1], "mf_capacity": 4},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2], "mf_capacity": 10},
            {"parent_vertex_id": _[1], "child_vertex_id": _[3], "mf_capacity": 12},
            {"parent_vertex_id": _[2], "child_vertex_id": _[4], "mf_capacity": 14},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2], "mf_capacity": 9},
            {"parent_vertex_id": _[3], "child_vertex_id": _[5], "mf_capacity": 20},
            {"parent_vertex_id": _[4], "child_vertex_id": _[3], "mf_capacity": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5], "mf_capacity": 4}
        )
        self.db.maximum_flow("test", 0, 5)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, mf_flow
                FROM edge
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 12),
                (1, 11),
                (2, 0),
                (3, 0),
                (4, 12),
                (5, 11),
                (6, 0),
                (7, 19),
                (8, 7),
                (9, 4)
            ]
        )

    def test_handle_cormen_etal_super_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(14)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[0], "child_vertex_id": _[2], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[0], "child_vertex_id": _[3], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[0], "child_vertex_id": _[4], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[0], "child_vertex_id": _[5], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[12], "child_vertex_id": _[13], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[11], "child_vertex_id": _[13], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[10], "child_vertex_id": _[13], "mf_capacity": 2**32 - 1},
            {"parent_vertex_id": _[1], "child_vertex_id": _[6], "mf_capacity": 10},
            {"parent_vertex_id": _[2], "child_vertex_id": _[6], "mf_capacity": 12},
            {"parent_vertex_id": _[2], "child_vertex_id": _[7], "mf_capacity": 5},
            {"parent_vertex_id": _[3], "child_vertex_id": _[7], "mf_capacity": 8},
            {"parent_vertex_id": _[3], "child_vertex_id": _[8], "mf_capacity": 14},
            {"parent_vertex_id": _[4], "child_vertex_id": _[8], "mf_capacity": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[9], "mf_capacity": 11},
            {"parent_vertex_id": _[5], "child_vertex_id": _[9], "mf_capacity": 2},
            {"parent_vertex_id": _[6], "child_vertex_id": _[10], "mf_capacity": 3},
            {"parent_vertex_id": _[7], "child_vertex_id": _[10], "mf_capacity": 15},
            {"parent_vertex_id": _[7], "child_vertex_id": _[11], "mf_capacity": 6},
            {"parent_vertex_id": _[8], "child_vertex_id": _[11], "mf_capacity": 20},
            {"parent_vertex_id": _[8], "child_vertex_id": _[12], "mf_capacity": 13},
            {"parent_vertex_id": _[9], "child_vertex_id": _[12], "mf_capacity": 18}
        )
        self.db.maximum_flow("test", 0, 13)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, mf_flow
                FROM edge
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 3),
                (1, 5),
                (2, 22),
                (3, 18),
                (4, 2),
                (5, 14),
                (6, 20),
                (7, 16),
                (8, 3),
                (9, 0),
                (10, 5),
                (11, 8),
                (12, 14),
                (13, 7),
                (14, 11),
                (15, 2),
                (16, 3),
                (17, 13),
                (18, 0),
                (19, 20),
                (20, 1),
                (21, 13)
            ]
        )


class TestFlowNetworkWalkVBF(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("flow_network_walk_vbf", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.flow_network_walk_vbf))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.flow_network_walk_vbf)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 4)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        source_vertex_id = s.parameters["source_vertex_id"]
        self.assertEqual(source_vertex_id.default, source_vertex_id.empty)
        self.assertEqual(source_vertex_id.kind, source_vertex_id.POSITIONAL_OR_KEYWORD)

        sink_vertex_id = s.parameters["sink_vertex_id"]
        self.assertEqual(sink_vertex_id.default, sink_vertex_id.empty)
        self.assertEqual(sink_vertex_id.kind, sink_vertex_id.POSITIONAL_OR_KEYWORD)

    def test_handle_cormen_etal_example(self):
        """"""
        self.db.create_graph("test", 1, 0)
        _ = self.db.add_vertices("test", *[{} for _ in range(6)])
        _ = self.db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1], "mf_capacity": 16},
            {"parent_vertex_id": _[0], "child_vertex_id": _[2], "mf_capacity": 13},
            {"parent_vertex_id": _[2], "child_vertex_id": _[1], "mf_capacity": 4},
            {"parent_vertex_id": _[1], "child_vertex_id": _[3], "mf_capacity": 12},
            {"parent_vertex_id": _[2], "child_vertex_id": _[4], "mf_capacity": 14},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2], "mf_capacity": 9},
            {"parent_vertex_id": _[3], "child_vertex_id": _[5], "mf_capacity": 20},
            {"parent_vertex_id": _[4], "child_vertex_id": _[3], "mf_capacity": 7},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5], "mf_capacity": 4}
        )

        # test augmenting path with one of sink's edges
        self.db.flow_network_walk_vbf("test", 0, 5)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 2, None, 0),
                (1, 2, 0, 1),
                (2, 2, 0, 1),
                (3, 2, 1, 2),
                (4, 2, 2, 2),
                (5, 2, 3, 3)
            ],
        )

        # test augmenting path with the other edge
        self.db.alter_edge(6, mf_flow=21)
        self.db.flow_network_walk_vbf("test", 0, 5)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("""
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                ORDER BY id
                """)
            ).fetchall(),
            [
                (0, 2, None, 0),
                (1, 2, 0, 1),
                (2, 2, 0, 1),
                (3, 2, 1, 2),
                (4, 2, 2, 2),
                (5, 2, 4, 3)
            ],
        )
