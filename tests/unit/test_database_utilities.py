import functools
import inspect
import itertools
import sys

import giraffe

from . import FreshModelTestCase


class TestClose(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("close", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.close))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.close)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 1)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

    def test_closes_connection(self):
        """"""
        db = giraffe.Database(self.con)
        self.assertEqual(db.cursor.execute("SELECT 1").fetchone()[0], 1)
        db.close()
        with self.assertRaises(sys.modules[self.con.__module__].Error):
            db.cursor.execute("SELECT 1")


class TestCheckMode(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("check_mode", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.check_mode))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.check_mode)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        flags = s.parameters["flags"]
        self.assertEqual(flags.default, graph.empty)
        self.assertEqual(flags.kind, flags.VAR_POSITIONAL)

    def test_flags_are_small_powers_of_two(self):
        """"""
        self.assertEqual(2, giraffe.VEIM)
        self.assertEqual(4, giraffe.EDIM)
        self.assertEqual(8, giraffe.CYIM)
        self.assertEqual(16, giraffe.CEIM)

    def test_no_graph_mode_always_returns_false(self):
        """"""
        self.con.execute("INSERT INTO graph (id, directed) VALUES ('x', 0)")
        db = giraffe.Database(self.con)
        self.assertFalse(db.check_mode("x"))
        for i in range(1, 5):
            for combo in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, combo)
                self.assertFalse(db.check_mode("x", flags))

    def test_all_flag_combos_return_true(self):
        """"""
        self.con.execute("INSERT INTO graph (id, directed) VALUES ('x', 0)")
        db = giraffe.Database(self.con)
        for i in range(1, 5):
            for combo in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, combo)
                db.cursor.execute("UPDATE graph SET mode = ?", (flags,))
                db.connection.commit()
                self.assertTrue(db.check_mode("x", flags))


class TestCreateGraph(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("create_graph", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.create_graph))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.create_graph)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 6)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        name = s.parameters["name"]
        self.assertEqual(name.default, name.empty)
        self.assertEqual(name.kind, name.POSITIONAL_OR_KEYWORD)

        directed = s.parameters["directed"]
        self.assertEqual(directed.default, directed.empty)
        self.assertEqual(directed.kind, directed.POSITIONAL_OR_KEYWORD)

        acyclic = s.parameters["acyclic"]
        self.assertEqual(acyclic.default, None)
        self.assertEqual(acyclic.kind, acyclic.POSITIONAL_OR_KEYWORD)

        mode = s.parameters["mode"]
        self.assertEqual(mode.default, 0)
        self.assertEqual(mode.kind, mode.POSITIONAL_OR_KEYWORD)

        metadata = s.parameters["metadata"]
        self.assertEqual(metadata.default, metadata.empty)
        self.assertEqual(metadata.kind, metadata.VAR_KEYWORD)

    def test_raises_with_no_parameters(self):
        """"""
        db = giraffe.Database(self.con)
        with self.assertRaises(Exception):
            db.create_graph("test_name")

    def test_raises_without_directed(self):
        """"""
        db = giraffe.Database(self.con)
        with self.assertRaises(TypeError):
            db.create_graph("test_name", acyclic=0, mode=0, metadatum="x")

    def test_creates_directed_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 1)
        self.assertEqual(
            [("test_graph", 1, None, None, 0)],
            db.cursor.execute("SELECT * FROM graph").fetchall(),
        )

    def test_creates_undirected_graph(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 0)
        self.assertEqual(
            [("test_graph", 0, None, None, 0)],
            db.cursor.execute("SELECT * FROM graph").fetchall(),
        )

    def test_raises_pk_constraint_violation(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 0)
        with self.assertRaises(sys.modules[db.connection.__module__].IntegrityError):
            db.create_graph("test_graph", 0)

    def test_metadata_created(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("x", 1, bork=1)
        self.assertEqual(
            db.cursor.execute("SELECT * FROM graph").fetchall(),
            [("x", 1, None, '{"bork": 1}', 0)],
        )


class TestAlterGraph(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("alter_graph", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.alter_graph))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.alter_graph)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        name = s.parameters["name"]
        self.assertEqual(name.default, name.empty)
        self.assertEqual(name.kind, name.POSITIONAL_OR_KEYWORD)

        attributes = s.parameters["attributes"]
        self.assertEqual(attributes.default, attributes.empty)
        self.assertEqual(attributes.kind, attributes.VAR_KEYWORD)

    def test_raise_if_altering_using_no_attributes(self):
        """"""
        db = giraffe.Database(self.con)

        # create a graph and fetch it with fetchall
        db.create_graph("test_graph", 0)

        # alter with no attributes
        with self.assertRaises(Exception):
            db.alter_graph("test_graph")

    def test_raise_if_using_at_least_one_invalid_attribute(self):
        """"""
        db = giraffe.Database(self.con)

        # create a graph and fetch it with fetchall
        db.create_graph("test_graph", 0)

        # alter with bad attributes
        with self.assertRaises(Exception):
            db.alter_graph("test_graph", password=7)

    def test_good_attributes_are_inserted(self):
        """"""
        db = giraffe.Database(self.con)

        # create a graph and fetch it with fetchall
        db.create_graph("test_graph", 0)
        old_db_row = db.cursor.execute("SELECT * FROM graph").fetchone()

        # alter with new attributes
        db.alter_graph(
            "test_graph",
            directed=1,
            acyclic=1,
            metadata={"something": 1},
            mode=giraffe.VEIM,
        )
        new_db_row = db.cursor.execute("SELECT * FROM graph").fetchone()

        # assert graph id is the same
        self.assertEqual(old_db_row[0], new_db_row[0])

        # assert old record is different from new record (except id)
        map(
            lambda x, y: self.assertNotEqual(x, y),
            zip(old_db_row[1:], new_db_row[1:]),
        )

        # assert new record has the chosen attributes
        map(
            lambda x, y: self.assertEqual(x, y),
            zip(("test_graph", 1, 1, '{"something": 1}', giraffe.VEIM), new_db_row),
        )


class TestDeleteGraphs(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("delete_graphs", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.delete_graphs))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.delete_graphs)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 2)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        names = s.parameters["names"]
        self.assertEqual(names.default, names.empty)
        self.assertEqual(names.kind, names.VAR_POSITIONAL)

    def test_graph_is_deleted(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 0)
        db.delete_graphs("test_graph")
        self.assertEqual(db.cursor.execute("SELECT * FROM graph").fetchall(), [])


class TestAddVertices(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("add_vertices", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.add_vertices))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.add_vertices)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        vertices = s.parameters["vertices"]
        self.assertEqual(vertices.default, vertices.empty)
        self.assertEqual(vertices.kind, vertices.VAR_POSITIONAL)

    def test_raise_if_at_least_one_bad_attribute(self):
        """"""
        db = giraffe.Database(self.con)

        # create the graph
        db.create_graph("test_graph", 0)

        # try inserting some bad vertices
        with self.assertRaises(Exception):
            db.add_vertices("test_graph", {7: 8}, {"hi": "bye"})

    def test_vertices_are_added(self):
        """"""
        db = giraffe.Database(self.con)

        # create the graph
        db.create_graph("test_graph", 0)

        # add some vertices
        vertex_ids = db.add_vertices(
            "test_graph",
            {"tree": 7, "metadata": {1: 2}},
            {"color": 2, "metadata": {1: 3}},
        )

        # assert returned ids are correct
        self.assertEqual(vertex_ids, [0, 1])

        # fetch the new vertices and assert they are equal to input
        self.assertEqual(
            db.cursor.execute(
                "SELECT * FROM vertex WHERE graph_id = 'test_graph'"
            ).fetchall(),
            [
                (
                    0,
                    None,
                    "test_graph",
                    None,
                    None,
                    None,
                    None,
                    7,
                    0,
                    '{"1": 2}',
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
                (
                    1,
                    None,
                    "test_graph",
                    None,
                    None,
                    None,
                    None,
                    None,
                    2,
                    '{"1": 3}',
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )


class TestAlterVertex(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("alter_vertex", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.alter_vertex))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.alter_vertex)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        vertex_id = s.parameters["vertex_id"]
        self.assertEqual(vertex_id.default, vertex_id.empty)
        self.assertEqual(vertex_id.kind, vertex_id.POSITIONAL_OR_KEYWORD)

        attributes = s.parameters["attributes"]
        self.assertEqual(attributes.default, attributes.empty)
        self.assertEqual(attributes.kind, attributes.VAR_KEYWORD)

    def test_raise_if_altering_using_no_attributes(self):
        """"""
        db = giraffe.Database(self.con)

        # create a graph and fetch it with fetchall
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {})

        # alter with no attributes
        with self.assertRaises(Exception):
            db.alter_vertex(vertex_ids[0])

    def test_raise_if_using_at_least_one_invalid_attribute(self):
        """"""
        db = giraffe.Database(self.con)

        # create a graph and fetch it with fetchall
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {})

        # alter with bad attributes
        with self.assertRaises(Exception):
            db.alter_vertex(vertex_ids[0], password=7)

    def test_good_attributes_are_inserted(self):
        """"""
        db = giraffe.Database(self.con)

        # create a graph and fetch it with fetchall
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {})

        # assert color is 0
        color = db.cursor.execute(
            "SELECT color FROM vertex WHERE id = ?", vertex_ids
        ).fetchone()[0]
        self.assertEqual(color, 0)

        # alter with new attributes
        db.alter_vertex(vertex_ids[0], color=1)
        color = db.cursor.execute(
            "SELECT color FROM vertex WHERE id = ?", vertex_ids
        ).fetchone()[0]

        # assert graph id is the same
        self.assertEqual(color, 1)


class TestDeleteVertices(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("delete_vertices", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.delete_vertices))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.delete_vertices)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 2)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        ids = s.parameters["ids"]
        self.assertEqual(ids.default, ids.empty)
        self.assertEqual(ids.kind, ids.VAR_POSITIONAL)

    def test_vertex_is_deleted(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {})
        db.delete_vertices(*vertex_ids)
        self.assertEqual(db.cursor.execute("SELECT * FROM vertex").fetchall(), [])


class TestAddEdges(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("add_edges", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.add_edges))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.add_edges)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        graph = s.parameters["graph"]
        self.assertEqual(graph.default, graph.empty)
        self.assertEqual(graph.kind, graph.POSITIONAL_OR_KEYWORD)

        edges = s.parameters["edges"]
        self.assertEqual(edges.default, edges.empty)
        self.assertEqual(edges.kind, edges.VAR_POSITIONAL)

    def test_bad_edge_attributes_raise(self):
        """"""
        db = giraffe.Database(self.con)

        # create the graph
        db.create_graph("test_graph", 0)

        # try inserting some bad vertices
        with self.assertRaises(Exception):
            db.add_edges("test_graph", {7: 8}, {"hi": "bye"})

    def test_edges_are_added(self):
        """"""
        db = giraffe.Database(self.con)

        # create the graph
        db.create_graph("test_graph", 0)

        # add edges
        vertex_ids = db.add_vertices("test_graph", {}, {})

        # add a vertex whose id is None
        db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[1]},
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )

        # assert id is autoincrementing
        self.assertEqual(
            db.cursor.execute("SELECT * FROM edge").fetchall(),
            [
                (
                    0,
                    None,
                    None,
                    0,
                    1,
                    "test_graph",
                    None,
                    None,
                    0,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
                (
                    1,
                    None,
                    None,
                    0,
                    0,
                    "test_graph",
                    None,
                    None,
                    0,
                    None,
                    None,
                    None,
                    None,
                    None,
                    None,
                ),
            ],
        )

    def test_raises_fk_constraint_violation(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 0)
        with self.assertRaises(sys.modules[db.connection.__module__].IntegrityError):
            db.add_edges("test_graph", {})


class TestAlterEdge(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("alter_edge", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.alter_edge))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.alter_edge)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 3)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        vertex_id = s.parameters["edge_id"]
        self.assertEqual(vertex_id.default, vertex_id.empty)
        self.assertEqual(vertex_id.kind, vertex_id.POSITIONAL_OR_KEYWORD)

        attributes = s.parameters["attributes"]
        self.assertEqual(attributes.default, attributes.empty)
        self.assertEqual(attributes.kind, attributes.VAR_KEYWORD)

    def test_raise_if_altering_using_no_attributes(self):
        """"""
        db = giraffe.Database(self.con)

        # alter with no attributes
        with self.assertRaises(Exception):
            db.alter_edge(1)

    def test_raise_if_using_at_least_one_invalid_attribute(self):
        """"""
        db = giraffe.Database(self.con)

        # set up a graph
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {})
        edge_ids = db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )

        # alter graph edge with bad attributes
        with self.assertRaises(Exception):
            db.alter_edge(edge_ids[0], password=7)

    def test_good_attributes_are_inserted(self):
        """"""
        db = giraffe.Database(self.con)

        # set up a graph
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {})
        edge_ids = db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )

        # assert color is 0
        color = db.cursor.execute(
            "SELECT color FROM edge WHERE id = ?", edge_ids
        ).fetchone()[0]
        self.assertEqual(color, 0)

        # alter with new attributes and assert change
        db.alter_edge(edge_ids[0], color=1)
        color = db.cursor.execute(
            "SELECT color FROM edge WHERE id = ?", vertex_ids
        ).fetchone()[0]
        self.assertEqual(color, 1)


class TestDeleteEdges(FreshModelTestCase):
    """"""

    def test_is_in_gqlite(self):
        """"""
        self.assertIn("delete_edges", dir(giraffe.Database))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Database.delete_edges))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Database.delete_edges)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 2)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

        ids = s.parameters["ids"]
        self.assertEqual(ids.default, ids.empty)
        self.assertEqual(ids.kind, ids.VAR_POSITIONAL)

    def test_edge_is_deleted(self):
        """"""
        db = giraffe.Database(self.con)
        db.create_graph("test_graph", 0)
        vertex_ids = db.add_vertices("test_graph", {"tree": 1})
        edge_ids = db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )
        db.delete_edges(*edge_ids)
        self.assertEqual(db.cursor.execute("SELECT * FROM edge").fetchall(), [])
