import functools
import inspect
import itertools

import giraffe

from . import FreshModelTestCase


class TestDFSearch(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("df_search", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.df_search))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.df_search)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        hooks = s.parameters["hooks"]
        self.assertEqual(hooks.default, hooks.empty)
        self.assertEqual(hooks.kind, hooks.VAR_KEYWORD)

    def test_raise_on_immutable_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.cursor.execute("INSERT INTO graph (id, directed) VALUES ('x', 0)")
        db.connection.commit()

        for i in range(1, 5):
            for c in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, c)
                db.cursor.execute("UPDATE graph SET mode = ?", (flags,))
                db.connection.commit()
                with self.assertRaises(Exception):
                    db.df_search("x")

    def test_do_nothing_with_empty_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.cursor.execute("INSERT INTO graph (id, directed) VALUES ('test', 0)")
        db.connection.commit()
        self.assertIs(db.df_search("test"), None)

    def test_handle_single_self_loop(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        db.add_vertices("test", {})
        db.add_edges("test", {"parent_vertex_id": 0, "child_vertex_id": 0})

        db.df_search("test")

        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [(0, 0, 0, 0, 2, 0, 1)],
        )

    def test_handle_isolated_components(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1, 0)
        db.add_vertices("test", *[{"metadata": {}} for _ in range(4)])
        db.add_edges(
            "test",
            {"parent_vertex_id": 0, "child_vertex_id": 1},
            {"parent_vertex_id": 2, "child_vertex_id": 3},
        )

        db.df_search("test")

        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [(0, 1, 0, 0, 2, 0, 1), (1, 3, 2, 1, 2, 2, 3)],
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

        db.df_search("test")

        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [
                (0, 1, 0, 0, 2, 0, 29),
                (1, 2, 1, 0, 2, 1, 24),
                (2, 3, 2, 0, 2, 2, 19),
                (3, 4, 3, 0, 2, 3, 14),
                (4, 0, 4, 0, 2, 4, 9),
                (5, 5, 0, 0, 2, 5, 6),
                (6, 6, 1, 0, 2, 25, 26),
                (7, 7, 2, 0, 2, 20, 21),
                (8, 8, 3, 0, 2, 15, 16),
                (9, 9, 4, 0, 2, 10, 11),
                (10, 6, 0, 0, 2, 7, 8),
                (11, 7, 1, 0, 2, 27, 28),
                (12, 8, 2, 0, 2, 22, 23),
                (13, 9, 3, 0, 2, 17, 18),
                (14, 5, 4, 0, 2, 12, 13),
            ],
        )

    def test_handle_peterson(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_peterson("test")

        db.df_search("test")

        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [
                (0, 1, 0, 0, 2, 0, 29),
                (1, 2, 1, 0, 2, 1, 26),
                (2, 3, 2, 0, 2, 2, 23),
                (3, 4, 3, 0, 2, 3, 20),
                (4, 0, 4, 0, 2, 4, 17),
                (5, 5, 0, 0, 2, 5, 16),
                (6, 6, 1, 0, 2, 27, 28),
                (7, 7, 2, 0, 2, 24, 25),
                (8, 8, 3, 0, 2, 21, 22),
                (9, 9, 4, 0, 2, 18, 19),
                (10, 6, 5, 0, 2, 6, 15),
                (11, 7, 6, 0, 2, 7, 14),
                (12, 8, 7, 0, 2, 8, 13),
                (13, 9, 8, 0, 2, 9, 12),
                (14, 5, 9, 0, 2, 10, 11),
            ],
        )

    def test_handle_frucht(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        vertex_ids = db.add_vertices("test", *[{"metadata": {}} for _ in range(12)])
        edge_ids = db.add_edges(
            "test",
            {"parent_vertex_id": 0, "child_vertex_id": 10},
            {"parent_vertex_id": 10, "child_vertex_id": 11},
            {"parent_vertex_id": 11, "child_vertex_id": 8},
            {"parent_vertex_id": 8, "child_vertex_id": 6},
            {"parent_vertex_id": 4, "child_vertex_id": 6},
            {"parent_vertex_id": 4, "child_vertex_id": 3},
            {"parent_vertex_id": 3, "child_vertex_id": 0},
            {"parent_vertex_id": 0, "child_vertex_id": 1},
            {"parent_vertex_id": 9, "child_vertex_id": 10},
            {"parent_vertex_id": 11, "child_vertex_id": 9},
            {"parent_vertex_id": 8, "child_vertex_id": 7},
            {"parent_vertex_id": 6, "child_vertex_id": 7},
            {"parent_vertex_id": 4, "child_vertex_id": 2},
            {"parent_vertex_id": 2, "child_vertex_id": 3},
            {"parent_vertex_id": 1, "child_vertex_id": 2},
            {"parent_vertex_id": 1, "child_vertex_id": 5},
            {"parent_vertex_id": 7, "child_vertex_id": 5},
            {"parent_vertex_id": 5, "child_vertex_id": 9},
        )

        db.df_search("test")

        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [
                (0, 10, 0, 0, 2, 0, 19),
                (1, 11, 10, 0, 2, 1, 18),
                (2, 8, 11, 0, 2, 2, 15),
                (3, 6, 8, 0, 2, 3, 12),
                (4, 6, 4, 4, 2, 20, 21),
                (5, 3, 4, 5, 2, 22, 33),
                (6, 0, 3, 5, 2, 23, 32),
                (7, 1, 0, 5, 2, 24, 31),
                (8, 10, 9, 0, 2, 7, 8),
                (9, 9, 11, 0, 2, 16, 17),
                (10, 7, 8, 0, 2, 13, 14),
                (11, 7, 6, 0, 2, 4, 11),
                (12, 2, 4, 12, 2, 34, 35),
                (13, 3, 2, 5, 2, 26, 27),
                (14, 2, 1, 5, 2, 25, 28),
                (15, 5, 1, 5, 2, 29, 30),
                (16, 5, 7, 0, 2, 5, 10),
                (17, 9, 5, 0, 2, 6, 9),
            ],
        )

    def test_handle_weird_loop(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        db.add_vertices("test", *[{} for _ in range(15)])
        db.add_edges(
            "test",
            {"parent_vertex_id": 0, "child_vertex_id": 1},
            {"parent_vertex_id": 1, "child_vertex_id": 2},
            {"parent_vertex_id": 2, "child_vertex_id": 3},
            {"parent_vertex_id": 3, "child_vertex_id": 4},
            {"parent_vertex_id": 4, "child_vertex_id": 5},
            {"parent_vertex_id": 5, "child_vertex_id": 6},
            {"parent_vertex_id": 6, "child_vertex_id": 7},
            {"parent_vertex_id": 2, "child_vertex_id": 8},
            {"parent_vertex_id": 8, "child_vertex_id": 9},
            {"parent_vertex_id": 9, "child_vertex_id": 10},
            {"parent_vertex_id": 10, "child_vertex_id": 11},
            {"parent_vertex_id": 11, "child_vertex_id": 12},
            {"parent_vertex_id": 12, "child_vertex_id": 13},
            {"parent_vertex_id": 13, "child_vertex_id": 14},
            {"parent_vertex_id": 14, "child_vertex_id": 0},
        )
        db.df_search("test")
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [
                (0, 1, 0, 0, 2, 0, 29),
                (1, 2, 1, 0, 2, 1, 28),
                (2, 3, 2, 0, 2, 2, 11),
                (3, 4, 3, 0, 2, 3, 10),
                (4, 5, 4, 0, 2, 4, 9),
                (5, 6, 5, 0, 2, 5, 8),
                (6, 7, 6, 0, 2, 6, 7),
                (7, 8, 2, 0, 2, 12, 27),
                (8, 9, 8, 0, 2, 13, 26),
                (9, 10, 9, 0, 2, 14, 25),
                (10, 11, 10, 0, 2, 15, 24),
                (11, 12, 11, 0, 2, 16, 23),
                (12, 13, 12, 0, 2, 17, 22),
                (13, 14, 13, 0, 2, 18, 21),
                (14, 0, 14, 0, 2, 19, 20),
            ],
        )

    def test_handle_cormen_etal(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        _ = db.add_vertices("test", *[{"metadata": {}} for _ in range(8)])
        _ = db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[0]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[4]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[5], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[7], "child_vertex_id": _[7]},
        )
        db.df_search("test")
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, child_vertex_id, parent_vertex_id, tree, color, pushed, popped
                FROM edge
                """
            ).fetchall(),
            [
                (0, 1, 0, 0, 2, 0, 27),
                (1, 2, 1, 0, 2, 1, 18),
                (2, 3, 2, 0, 2, 2, 17),
                (3, 2, 3, 0, 2, 3, 14),
                (4, 7, 3, 0, 2, 15, 16),
                (5, 6, 2, 0, 2, 4, 13),
                (6, 5, 1, 0, 2, 19, 20),
                (7, 0, 4, 0, 2, 22, 23),
                (8, 4, 1, 0, 2, 21, 26),
                (9, 5, 4, 0, 2, 24, 25),
                (10, 6, 5, 0, 2, 6, 11),
                (11, 5, 6, 0, 2, 5, 12),
                (12, 7, 6, 0, 2, 7, 10),
                (13, 7, 7, 0, 2, 8, 9),
            ],
        )


class TestDFFindCycles(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("find_cycles", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.find_cycles))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.find_cycles)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 2)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

    def test_handle_directed_peterson(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_peterson("test")
        db.find_cycles("test")

        # has two cycles
        self.assertEqual(
            db.cursor.execute("SELECT COUNT(*) FROM cycle").fetchone()[0], 2
        )

        # has the following parent/child relations
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT e.parent_vertex_id, e.child_vertex_id, ce.cycle_id
                FROM cycle_edge AS ce
                LEFT JOIN edge AS e
                    ON e.id = ce.edge_id
                ORDER BY ce.cycle_id
                """
            ).fetchall(),
            [
                (0, 1, 0),
                (1, 2, 0),
                (2, 3, 0),
                (3, 4, 0),
                (4, 0, 0),
                (5, 6, 1),
                (6, 7, 1),
                (7, 8, 1),
                (8, 9, 1),
                (9, 5, 1),
            ],
        )

    def test_handle_directed_frucht(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_frucht("test")
        db.find_cycles("test")

        # has two cycles
        self.assertEqual(
            db.cursor.execute("SELECT COUNT(*) FROM cycle").fetchone()[0], 4
        )

        # has the following parent/child relations
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT e.parent_vertex_id, e.child_vertex_id, ce.cycle_id
                FROM cycle_edge AS ce
                LEFT JOIN edge AS e
                    ON e.id = ce.edge_id
                ORDER BY ce.cycle_id
                """
            ).fetchall(),
            [
                (10, 11, 0),
                (11, 8, 0),
                (8, 6, 0),
                (9, 10, 0),
                (6, 7, 0),
                (7, 5, 0),
                (5, 9, 0),
                (10, 11, 1),
                (11, 8, 1),
                (9, 10, 1),
                (8, 7, 1),
                (7, 5, 1),
                (5, 9, 1),
                (10, 11, 2),
                (9, 10, 2),
                (11, 9, 2),
                (3, 0, 3),
                (0, 1, 3),
                (2, 3, 3),
                (1, 2, 3),
            ],
        )

    def test_handle_cycle_with_tail(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        _ = db.add_vertices("test", *[{"metadata": {}} for _ in range(15)])
        _ = db.add_edges(
            "test",
            {"parent_vertex_id": 0, "child_vertex_id": 1},
            {"parent_vertex_id": 1, "child_vertex_id": 2},
            {"parent_vertex_id": 2, "child_vertex_id": 3},
            {"parent_vertex_id": 3, "child_vertex_id": 4},
            {"parent_vertex_id": 4, "child_vertex_id": 5},
            {"parent_vertex_id": 5, "child_vertex_id": 6},
            {"parent_vertex_id": 6, "child_vertex_id": 7},
            {"parent_vertex_id": 2, "child_vertex_id": 8},
            {"parent_vertex_id": 8, "child_vertex_id": 9},
            {"parent_vertex_id": 9, "child_vertex_id": 10},
            {"parent_vertex_id": 10, "child_vertex_id": 11},
            {"parent_vertex_id": 11, "child_vertex_id": 12},
            {"parent_vertex_id": 12, "child_vertex_id": 13},
            {"parent_vertex_id": 13, "child_vertex_id": 14},
            {"parent_vertex_id": 14, "child_vertex_id": 0},
        )
        db.find_cycles("test")

        # has two cycles
        self.assertEqual(
            db.cursor.execute("SELECT COUNT(*) FROM cycle").fetchone()[0], 1
        )

        # has the following parent/child relations
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT e.parent_vertex_id, e.child_vertex_id, ce.cycle_id
                FROM cycle_edge AS ce
                LEFT JOIN edge AS e
                    ON e.id = ce.edge_id
                ORDER BY ce.cycle_id
                """
            ).fetchall(),
            [
                (0, 1, 0),
                (1, 2, 0),
                (2, 8, 0),
                (8, 9, 0),
                (9, 10, 0),
                (10, 11, 0),
                (11, 12, 0),
                (12, 13, 0),
                (13, 14, 0),
                (14, 0, 0),
            ],
        )


class TestTopologicalSort(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("topological_sort", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.topological_sort))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.topological_sort)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        search_hooks = s.parameters["search_hooks"]
        self.assertEqual(search_hooks.default, search_hooks.empty)
        self.assertEqual(search_hooks.kind, search_hooks.VAR_KEYWORD)

    def test_create_valid_permutation_with_cormen_etal_example(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        db.add_vertices("test", *[{} for _ in range(9)])
        db.add_edges(
            "test",
            {"parent_vertex_id": 0, "child_vertex_id": 1},
            {"parent_vertex_id": 1, "child_vertex_id": 2},
            {"parent_vertex_id": 2, "child_vertex_id": 5},
            {"parent_vertex_id": 3, "child_vertex_id": 2},
            {"parent_vertex_id": 3, "child_vertex_id": 4},
            {"parent_vertex_id": 4, "child_vertex_id": 5},
            {"parent_vertex_id": 0, "child_vertex_id": 6},
            {"parent_vertex_id": 1, "child_vertex_id": 7},
            {"parent_vertex_id": 6, "child_vertex_id": 7},
        )

        db.topological_sort("test")

        self.assertEqual(
            db.cursor.execute(
                "SELECT id FROM vertex WHERE graph_id = ? ORDER BY topological_id",
                ("test",),
            ).fetchall(),
            [(0,), (6,), (3,), (4,), (1,), (2,), (5,), (7,), (8,)],
        )

    def test_create_valid_permutation_with_three_in_a_row(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        db.add_vertices("test", *[{} for _ in range(3)])
        db.add_edges(
            "test",
            {"parent_vertex_id": 0, "child_vertex_id": 1},
            {"parent_vertex_id": 1, "child_vertex_id": 2},
            {"parent_vertex_id": 2, "child_vertex_id": 3},
        )

        db.topological_sort("test")

        self.assertEqual(
            db.cursor.execute(
                "SELECT id FROM vertex WHERE graph_id = ? ORDER BY topological_id",
                ("test",),
            ).fetchall(),
            [(0,), (1,), (2,)],
        )

    def test_raise_if_cycles(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        db.add_vertices("test", *[{} for _ in range(1)])
        db.add_edges("test", {"parent_vertex_id": 0, "child_vertex_id": 0})
        db.find_cycles("test")
        with self.assertRaises(Exception):
            db.topological_sort("test")


class TestStronglyConnectedComponents(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("strongly_connected_components", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.strongly_connected_components))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.strongly_connected_components)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 2)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

    def test_handle_three_component_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        db.add_vertices("test", *[{} for _ in range(7)])
        db.add_edges(
            "test",
            {"parent_vertex_id": 1, "child_vertex_id": 0},
            {"parent_vertex_id": 1, "child_vertex_id": 2},
            {"parent_vertex_id": 2, "child_vertex_id": 3},
            {"parent_vertex_id": 3, "child_vertex_id": 1},
            {"parent_vertex_id": 4, "child_vertex_id": 3},
            {"parent_vertex_id": 4, "child_vertex_id": 6},
            {"parent_vertex_id": 6, "child_vertex_id": 5},
            {"parent_vertex_id": 5, "child_vertex_id": 4},
        )

        db.strongly_connected_components("test")
        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, scc_index, scc_lowlink, scc_onstack
                FROM vertex
                ORDER BY id
                """
            ).fetchall(),
            [
                (0, 1, 1, 0),
                (1, 0, 0, 0),
                (2, 2, 0, 0),
                (3, 3, 0, 0),
                (4, 4, 4, 0),
                (5, 6, 4, 0),
                (6, 5, 4, 0),
            ],
        )

    def test_handle_cormen_etal(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        _ = db.add_vertices("test", *[{"metadata": {}} for _ in range(8)])
        _ = db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[0]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[4]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[5], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[7], "child_vertex_id": _[7]},
        )

        db.strongly_connected_components("test")

        self.assertEqual(
            db.cursor.execute(
                """
                SELECT id, scc_index, scc_lowlink, scc_onstack
                FROM vertex
                ORDER BY id
                """
            ).fetchall(),
            [
                (0, 0, 0, 0),
                (1, 1, 0, 0),
                (2, 2, 2, 0),
                (3, 3, 2, 0),
                (4, 7, 0, 0),
                (5, 5, 4, 0),
                (6, 4, 4, 0),
                (7, 6, 6, 0),
            ],
        )
