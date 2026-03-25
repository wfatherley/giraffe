import inspect

from . import FreshModelTestCase

import giraffe


class TestTranspose(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("transpose", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.transpose))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.transpose)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 4)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        transposed_name = s.parameters["transposed_name"]
        self.assertEqual(transposed_name.default, None)
        self.assertEqual(transposed_name.kind, transposed_name.POSITIONAL_OR_KEYWORD)

        chunk_size = s.parameters["chunk_size"]
        self.assertEqual(chunk_size.default, 250)
        self.assertEqual(chunk_size.kind, chunk_size.POSITIONAL_OR_KEYWORD)

    def test_raise_if_target_graph_edges_are_immutable(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", directed=1, mode=giraffe.EDIM)
        with self.assertRaises(Exception):
            db.transpose("test")

    def test_handle_two_vertex_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        _ = db.add_vertices("test", *[{} for _ in range(2)])
        db.add_edges("test", {"parent_vertex_id": _[0], "child_vertex_id": _[1]})

        transposed = db.transpose("test")

        # verify transposed graph record is correct
        transposed_graph = db.cursor.execute(
            "SELECT acyclic, directed, metadata FROM graph WHERE id = ?",
            (transposed,),
        ).fetchone()
        self.assertEqual(transposed_graph, (None, 1, '{"graph": "test"}'))

        # verify transposed vertices are correct
        transposed_vertices = db.cursor.execute(
            "SELECT metadata FROM vertex WHERE graph_id = ?", (transposed,)
        ).fetchall()
        self.assertIn(('{"graph": "test", "vertex": 0}',), transposed_vertices)
        self.assertIn(('{"graph": "test", "vertex": 1}',), transposed_vertices)

        # verify transpose edge is correct
        transposed_edge = db.cursor.execute(
            "SELECT id, parent_vertex_id, child_vertex_id, metadata FROM edge WHERE graph_id = ?",
            (transposed,),
        ).fetchone()
        self.assertEqual(
            transposed_edge[1:], (_[1], _[0], '{"graph": "test", "edge": 0}')
        )

        # verify original edge is correct
        self.assertEqual(
            transposed_edge[0],
            db.cursor.execute(
                "SELECT transpose_id FROM edge WHERE graph_id = 'test'"
            ).fetchone()[0],
        )

    def test_handle_three_vertex_graph_with_cycle(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test", 1)
        _ = db.add_vertices("test", *[{} for _ in range(3)])
        db.add_edges(
            "test",
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[0]},
        )
        # db.df_find_cycles("test")

        transposed = db.transpose("test")

        # verify transposed graph record is correct
        transposed_graph = db.cursor.execute(
            "SELECT acyclic, directed, metadata FROM graph WHERE id = ?",
            (transposed,),
        ).fetchone()
        self.assertEqual(transposed_graph, (None, 1, '{"graph": "test"}'))

        # verify transposed vertices are correct
        transposed_vertices = db.cursor.execute(
            "SELECT metadata FROM vertex WHERE graph_id = ?", (transposed,)
        ).fetchall()
        self.assertIn(('{"graph": "test", "vertex": 0}',), transposed_vertices)
        self.assertIn(('{"graph": "test", "vertex": 1}',), transposed_vertices)
        self.assertIn(('{"graph": "test", "vertex": 2}',), transposed_vertices)

        # verify transpose edge is correct
        transposed_edges = db.cursor.execute(
            "SELECT id, parent_vertex_id, child_vertex_id, metadata FROM edge WHERE graph_id = ?",
            (transposed,),
        ).fetchall()
        for transposed_edge in transposed_edges:
            self.assertIn(
                transposed_edge,
                [
                    (3, _[1], _[0], '{"graph": "test", "edge": 0}'),
                    (4, _[2], _[1], '{"graph": "test", "edge": 1}'),
                    (5, _[0], _[2], '{"graph": "test", "edge": 2}'),
                ],
            )

            # verify original edges has a transposed id
            self.assertTrue(
                db.cursor.execute(
                    "SELECT id FROM edge WHERE transpose_id = ?",
                    (transposed_edge[0],),
                ).fetchone()
            )
