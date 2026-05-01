import functools
import inspect
import itertools
import sys
import unittest

import giraffe
import sqlalchemy

from . import FreshModelTestCase


class TestRecordDictFactor(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("record_dict_factory", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.record_dict_factory))

    def test_signature_unchanged(self):
        """"""
        s = inspect.signature(giraffe.Giraffe.record_dict_factory)
        self.assertEqual(len(s.parameters), 2)

    def test_returns_dict(self):
        """"""
        self.assertIsInstance(self.db.record_dict_factory("vertex"), dict)



class TestLoadSchema(unittest.TestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("load_schema", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.load_schema))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.load_schema)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 1)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

    def test_creates_tables(self):
        """"""
        engine = sqlalchemy.create_engine("sqlite:///:memory:")
        db = giraffe.Giraffe(engine)
        db.load_schema()
        inspector = sqlalchemy.inspect(engine)
        self.assertIn("graph", inspector.get_table_names())
        self.assertIn("vertex", inspector.get_table_names())
        self.assertIn("edge", inspector.get_table_names())
        self.assertIn("cycle", inspector.get_table_names())
        self.assertIn("cycle_edge", inspector.get_table_names())
        db.close()
        engine.dispose()


class TestClose(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("close", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.close))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.close)

        # verify parameters are unchanged
        self.assertEqual(len(s.parameters), 1)

        fles = s.parameters["self"]
        self.assertEqual(fles.default, fles.empty)
        self.assertEqual(fles.kind, fles.POSITIONAL_OR_KEYWORD)

    def test_closes_connection(self):
        """"""
        dql = sqlalchemy.text("SELECT 1")
        self.assertEqual(self.db.connection.execute(dql).scalar_one(), 1)
        self.db.close()
        with self.assertRaises(sqlalchemy.exc.ResourceClosedError):
            self.db.connection.execute(dql)


class TestCheckMode(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("check_mode", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.check_mode))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.check_mode)

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
        self.db.create_graph("x", 0)
        self.assertFalse(self.db.check_mode("x"))
        for i in range(1, 5):
            for combo in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, combo)
                self.assertFalse(self.db.check_mode("x", flags))

    def test_all_flag_combos_return_true(self):
        """"""
        self.db.connection.execute(
            sqlalchemy.text("INSERT INTO graph (id, directed) VALUES ('x', 0)")
        )
        for i in range(1, 5):
            for combo in itertools.combinations(
                [giraffe.VEIM, giraffe.EDIM, giraffe.CYIM, giraffe.CEIM], i
            ):
                flags = functools.reduce(lambda x, y: x | y, combo)
                self.db.connection.execute(
                    sqlalchemy.text("UPDATE graph SET mode = :mode"), {"mode": flags}
                )
                self.assertTrue(self.db.check_mode("x", flags))


class TestCreateGraph(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("create_graph", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.create_graph))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.create_graph)

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

    def test_raises_with_no_directed_parameter(self):
        """"""
        with self.assertRaises(Exception):
            self.db.create_graph("test_name")

    def test_creates_directed_graph(self):
        """"""
        self.db.create_graph("test_graph", 1)
        self.assertEqual(
            [("test_graph", 1, None, None, 0)],
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM graph")
            ).fetchall(),
        )

    def test_creates_undirected_graph(self):
        """"""
        self.db.create_graph("test_graph", 0)
        self.assertEqual(
            [("test_graph", 0, None, None, 0)],
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM graph")
            ).fetchall(),
        )

    def test_raises_pk_constraint_violation(self):
        """"""
        self.db.create_graph("test_graph", 0)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.db.create_graph("test_graph", 0)

    def test_metadata_created(self):
        """"""
        self.db.create_graph("x", 1, bork=1)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM graph")
            ).fetchall(),
            [("x", 1, None, '{"bork": 1}', 0)],
        )


class TestAlterGraph(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("alter_graph", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.alter_graph))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.alter_graph)

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

        # create a graph and fetch it with fetchall
        self.db.create_graph("test_graph", 0)

        # alter with no attributes
        with self.assertRaises(Exception):
            self.db.alter_graph("test_graph")

    def test_raise_if_using_at_least_one_invalid_attribute(self):
        """"""

        # create a graph and fetch it with fetchall
        self.db.create_graph("test_graph", 0)

        # alter with bad attributes
        with self.assertRaises(Exception):
            self.db.alter_graph("test_graph", password=7)

    def test_good_attributes_are_inserted(self):
        """"""

        # create a graph and fetch it with fetchall
        self.db.create_graph("test_graph", 0)
        old_db_row = self.db.connection.execute(
            sqlalchemy.text("SELECT * FROM graph")
        ).fetchone()

        # alter with new attributes
        self.db.alter_graph(
            "test_graph",
            directed=1,
            acyclic=1,
            metadata={"something": 1},
            mode=giraffe.VEIM,
        )
        new_db_row = self.db.connection.execute(
            sqlalchemy.text("SELECT * FROM graph")
        ).fetchone()

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

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("delete_graphs", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.delete_graphs))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.delete_graphs)

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
        self.db.create_graph("test_graph", 0)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM graph")
            ).fetchall(),
            [("test_graph", 0, None, None, 0)],
        )
        self.db.delete_graphs("test_graph")
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM graph")
            ).fetchall(),
            [],
        )


class TestAddVertices(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("add_vertices", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.add_vertices))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.add_vertices)

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

        # create the graph
        self.db.create_graph("test_graph", 0)

        # try inserting some bad vertices
        with self.assertRaises(Exception):
            self.db.add_vertices("test_graph", {7: 8}, {"hi": "bye"})

    def test_vertices_are_added(self):
        """"""

        # create the graph
        self.db.create_graph("test_graph", 0)

        # add some vertices
        vertex_ids = self.db.add_vertices(
            "test_graph",
            {"tree": 7, "metadata": {1: 2}},
            {"color": 2, "metadata": {1: 3}},
        )

        # assert returned ids are correct
        self.assertEqual(vertex_ids, [0, 1])

        # fetch the new vertices and assert they are equal to input
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM vertex WHERE graph_id = :graph_id"),
                {"graph_id": "test_graph"},
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

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("alter_vertex", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.alter_vertex))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.alter_vertex)

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

        # create a graph and fetch it with fetchall
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {})

        # alter with no attributes
        with self.assertRaises(Exception):
            self.db.alter_vertex(vertex_ids[0])

    def test_raise_if_using_at_least_one_invalid_attribute(self):
        """"""

        # create a graph and fetch it with fetchall
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {})

        # alter with bad attributes
        with self.assertRaises(Exception):
            self.db.alter_vertex(vertex_ids[0], password=7)

    def test_good_attributes_are_inserted(self):
        """"""

        # create a graph and fetch it with fetchall
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {})

        # assert color is 0
        color = self.db.connection.execute(
            sqlalchemy.text("SELECT color FROM vertex WHERE id = :vertex_id"),
            {"vertex_id": vertex_ids[0]},
        ).fetchone()[0]
        self.assertEqual(color, 0)

        # alter with new attributes
        self.db.alter_vertex(vertex_ids[0], color=1)
        color = self.db.connection.execute(
            sqlalchemy.text("SELECT color FROM vertex WHERE id = :vertex_id"),
            {"vertex_id": vertex_ids[0]},
        ).fetchone()[0]

        # assert graph id is the same
        self.assertEqual(color, 1)


class TestDeleteVertices(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("delete_vertices", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.delete_vertices))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.delete_vertices)

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
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {})
        self.db.delete_vertices(*vertex_ids)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM vertex")
            ).fetchall(),
            [],
        )


class TestAddEdges(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("add_edges", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.add_edges))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.add_edges)

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

        # create the graph
        self.db.create_graph("test_graph", 0)

        # try inserting some bad vertices
        with self.assertRaises(Exception):
            self.db.add_edges("test_graph", {7: 8}, {"hi": "bye"})

    def test_edges_are_added(self):
        """"""

        # create the graph
        self.db.create_graph("test_graph", 0)

        # add edges
        vertex_ids = self.db.add_vertices("test_graph", {}, {})

        # add a vertex whose id is None
        self.db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[1]},
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )

        # assert id is autoincrementing
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM edge")
            ).fetchall(),
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
                    None,
                    0,
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
                    None,
                    0,
                ),
            ],
        )

    def test_raises_fk_constraint_violation(self):
        """"""
        self.db.create_graph("test_graph", 0)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.db.add_edges("test_graph", {})


class TestAlterEdge(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("alter_edge", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.alter_edge))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.alter_edge)

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

        # alter with no attributes
        with self.assertRaises(Exception):
            self.db.alter_edge(1)

    def test_raise_if_using_at_least_one_invalid_attribute(self):
        """"""

        # set up a graph
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {})
        edge_ids = self.db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )

        # alter graph edge with bad attributes
        with self.assertRaises(Exception):
            self.db.alter_edge(edge_ids[0], password=7)

    def test_good_attributes_are_inserted(self):
        """"""

        # set up a graph
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {})
        edge_ids = self.db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )

        # assert color is 0
        color = self.db.connection.execute(
            sqlalchemy.text("SELECT color FROM edge WHERE id = :id"),
            {"id": edge_ids[0]},
        ).scalar_one()
        self.assertEqual(color, 0)

        # alter with new attributes and assert change
        self.db.alter_edge(edge_ids[0], color=1)
        color = self.db.connection.execute(
            sqlalchemy.text("SELECT color FROM edge WHERE id = :id"),
            {"id": edge_ids[0]},
        ).scalar_one()
        self.assertEqual(color, 1)


class TestDeleteEdges(FreshModelTestCase):
    """"""

    def test_is_in_giraffe(self):
        """"""
        self.assertIn("delete_edges", dir(giraffe.Giraffe))

    def test_is_callable(self):
        """"""
        self.assertTrue(callable(giraffe.Giraffe.delete_edges))

    def test_signature_unchanged(self):
        """"""

        # fetch signature
        s = inspect.signature(giraffe.Giraffe.delete_edges)

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
        self.db.create_graph("test_graph", 0)
        vertex_ids = self.db.add_vertices("test_graph", {"tree": 1})
        edge_ids = self.db.add_edges(
            "test_graph",
            {"parent_vertex_id": vertex_ids[0], "child_vertex_id": vertex_ids[0]},
        )
        self.db.delete_edges(*edge_ids)
        self.assertEqual(
            self.db.connection.execute(
                sqlalchemy.text("SELECT * FROM edge")
            ).fetchall(),
            [],
        )
