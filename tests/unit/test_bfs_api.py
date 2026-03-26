import functools
import inspect
import itertools

import giraffe

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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)

        for i in range(1, 5):
            for c in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, c)
                db.cursor.execute("UPDATE graph SET mode = ?", (flags,))
                db.connection.commit()
                with self.assertRaises(Exception):
                    db.ebf_search("x")

    def test_raise_with_bad_start_vertex(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        with self.assertRaises(Exception):
            db.ebf_search("test", 2)

    def test_handle_cormen_etal_example(self):
        """"""

        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(8)])
        _ = db.add_edges(
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
        db.ebf_search("test", 1)
        self.assertEqual(
            db.cursor.execute(
                "SELECT id, predecessor FROM edge"
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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(10)])
        _ = db.add_edges(
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
        db.ebf_search("test", 0)
        self.assertEqual(
            db.cursor.execute(
                "SELECT id, predecessor FROM edge"
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
        db = giraffe.Database(self.con)
        db.create_peterson("test")
        db.ebf_search("test", 0)
        self.assertEqual(
            db.cursor.execute(
                "SELECT id, predecessor FROM edge"
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
        db = giraffe.Database(self.con)
        db.create_frucht("test")
        db.ebf_search("test", 0)
        self.assertEqual(
            db.cursor.execute(
                "SELECT id, predecessor FROM edge"
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
        self.assertEqual(len(s.parameters), 4)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        start_vertex_id = s.parameters["start_vertex_id"]
        self.assertEqual(start_vertex_id.default, start_vertex_id.empty)
        self.assertEqual(start_vertex_id.kind, start_vertex_id.POSITIONAL_OR_KEYWORD)

        hooks = s.parameters["hooks"]
        self.assertEqual(hooks.default, hooks.empty)
        self.assertEqual(hooks.kind, hooks.VAR_KEYWORD)

    def test_raise_on_immutable_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)

        for i in range(1, 5):
            for c in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, c)
                db.cursor.execute("UPDATE graph SET mode = ?", (flags,))
                db.connection.commit()
                with self.assertRaises(Exception):
                    db.vbf_search("x")

    def test_raise_with_bad_start_vertex(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        with self.assertRaises(Exception):
            db.vbf_search("test", 2)

    def test_handle_cormen_etal_example(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(8)])
        _ = db.add_edges(
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
        db.vbf_search("test", 1)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                """
            ).fetchall(),
            [
                (0, 2, 1, 1),
                (1, 2, None, 0),
                (2, 2, 5, 2),
                (3, 2, 2, 3),
                (4, 2, 0, 2),
                (5, 2, 1, 1),
                (6, 2, 5, 2),
                (7, 2, 6, 3),
            ],
        )

    def test_handle_weird_peterson(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(10)])
        _ = db.add_edges(
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
        db.vbf_search("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                """
            ).fetchall(),
            [
                (0, 2, None, 0),
                (1, 2, 0, 1),
                (2, 2, 1, 2),
                (3, 2, 4, 2),
                (4, 2, 0, 1),
                (5, 2, 0, 1),
                (6, 2, 0, 1),
                (7, 2, 1, 2),
                (8, 2, 2, 3),
                (9, 2, 4, 2),
            ],
        )

    def test_handle_peterson(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_peterson("test")
        db.vbf_search("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                """
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
        db = giraffe.Database(self.con)
        db.create_frucht("test")
        db.vbf_search("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, color, predecessor, bf_distance
                FROM vertex
                """
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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(9)])
        _ = db.add_edges(
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
        db.minimum_spanning_tree("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, predecessor
                FROM vertex
                """
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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(9)])
        _ = db.add_edges(
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
        db.minimum_spanning_tree("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, predecessor
                FROM vertex
                """
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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(10)])
        _ = db.add_edges(
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
        db.minimum_spanning_tree("test", 0)
        self.assertEqual(
            db.cursor.execute(
                "SELECT id, predecessor FROM vertex"
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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(5)])
        _ = db.add_edges(
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
        db.single_source_shortest_path("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, predecessor, sp_estimate
                FROM vertex
                """
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
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        _ = db.add_vertices("test", *[{} for _ in range(5)])
        _ = db.add_edges(
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
        db.single_source_shortest_path("test", 0)
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, predecessor, sp_estimate
                FROM vertex
                """
            ).fetchall(),
            [
                (0, None, 0),
                (1, 4, 8),
                (2, 1, 9),
                (3, 2, 13),
                (4, 0, 5)
            ]
        )
