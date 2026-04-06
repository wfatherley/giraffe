"""A database-oriented library for handling graphs.

Giraffe provides tools to create and manipulate graphs that reside in
a relational database. Given a PEP-249 connection,
:class:`giraffe.Database` can create and analyze this simple model:

.. raw:: html

   <object data="mermaid/model.svg" type="image/svg+xml"></object>


Giraffe provides common CRUD-like functions to manage them graphs
stored with this model, and provides several common analytical methods,
such as :method:`giraffe.Database.topological_sort`.
"""

import json
import math
import string
import sys

from collections import OrderedDict
from enum import IntEnum
from itertools import groupby


def vertex_odict_factory() -> OrderedDict:
    """Return ordered mapping of vertex columns and their defaults.

    Return an instance of ``collections.OrderedDict``, with keys
    corresponding to the attributes (columns) of the vertex object
    (table). The values are the defaults specified in the vertex DDL.

    :return collections.OrderedDict:
    """
    return OrderedDict(
        **{
            "id": None,
            "predecessor": None,
            "graph_id": None,
            "aux_id": None,
            "bf_distance": None,
            "pushed": None,
            "popped": None,
            "tree": None,
            "color": 0,
            "metadata": None,
            "sp_estimate": None,
            "topological_id": None,
            "scc_index": None,
            "scc_lowlink": None,
            "scc_onstack": None,
            "mst_key": None,
        }
    )


def edge_odict_factory() -> OrderedDict:
    """Return ordered mapping of edge columns and their defaults.

    Return an instance of ``collections.OrderedDict``, with keys
    corresponding to the attributes (columns) of the edge object
    (table). The values are the defaults specified in the edge DDL.

    :return collections.OrderedDict:"""
    return OrderedDict(
        **{
            "id": None,
            "transpose_id": None,
            "predecessor": None,
            "parent_vertex_id": None,
            "child_vertex_id": None,
            "graph_id": None,
            "type": None,
            "tree": None,
            "color": 0,
            "pushed": None,
            "popped": None,
            "component_graph_bridge": None,
            "metadata": None,
            "weight": None,
            "aux_id": None,
            "mf_capacity": None,
            "mf_flow": 0,
        }
    )


# "is immutable" flags
VEIM = 2  # vertices
EDIM = 4  # edges
CYIM = 8  # cycles
CEIM = 16  # cycle edges


class Color(IntEnum):
    """Color-to-integer enumeration for anayltical algorithms."""

    white = 0
    gray = 1
    black = 2


class Database:
    """Composition of one database connection and graph methods.

    Primary interface for users of Giraffe. Given a live PEP-249
    connection object, provide attributes and methods for use in
    handling graphs that reside in the database. All methods call the
    connection's commit method after completing.

    Instances have the following attributes:

    .. py:attribute:: connection

        The PEP-249 compliant database connection passed in at
        customization time.

    .. py:attribute:: cursor

        A cursor instance created at customization time by calling
        ``Database.connection.cursor``.

    .. py:attribute:: model

        The working DDL under which graphs are created and manipulated.

    .. py:attribute:: sql

        The SQL queries used to perform the various routines (depth
        first search, etc.) are stored in this attribute
        ``Database.sql``. Before instantiation, the query parameters
        are written with Python's formatting minilangauge. After
        intstantiation, the query parameters are written in accord with
        the connection's ``paramstyle`` attribute.
    """

    sql = [
        """
        CREATE TABLE graph(

            id TEXT NOT NULL,

            directed INT NOT NULL,
            acyclic INT,
            metadata TEXT,
            mode int DEFAULT 0,

            PRIMARY KEY (id)
        );


        CREATE TABLE vertex(

            id INT PRIMARY KEY,
            predecessor INT REFERENCES vertex(id)
                ON DELETE SET NULL,

            graph_id TEXT NOT NULL,

            aux_id TEXT,
            bf_distance INT,
            pushed INT,
            popped INT,
            tree INT,
            color INT DEFAULT 0,
            metadata TEXT,
            sp_estimate NUMERIC,
            topological_id INT,
            scc_index INT,
            scc_lowlink INT,
            scc_onstack INT,
            mst_key NUMERIC,

            FOREIGN KEY (graph_id) REFERENCES graph(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );


        CREATE TABLE edge(

            id INT PRIMARY KEY,
            transpose_id INT REFERENCES edge(id)
                ON DELETE SET NULL,
            predecessor INT REFERENCES edge(id),

            parent_vertex_id INTEGER NOT NULL,
            child_vertex_id INTEGER NOT NULL,

            graph_id TEXT NOT NULL,
            
            type INT,
            tree INT,
            color INT DEFAULT 0,
            pushed INT,
            popped INT,
            component_graph_bridge INT,
            metadata TEXT,
            weight NUMERIC,
            aux_id TEXT,
            mf_capacity NUMERIC,
            mf_flow NUMERIC DEFAULT 0,

            FOREIGN KEY (graph_id) REFERENCES graph(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            FOREIGN KEY (parent_vertex_id) REFERENCES vertex(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            FOREIGN KEY (child_vertex_id) REFERENCES vertex(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );


        CREATE TABLE cycle(
            graph_id TEXT NOT NULL,
            cardinality INT NOT NULL,
            inflows INT,
            outflows INT,
            metadata TEXT,

            id INT PRIMARY KEY,

            FOREIGN KEY (graph_id) REFERENCES graph(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );


        CREATE TABLE cycle_edge(
            cycle_id NOT NULL,
            edge_id NOT NULL,

            FOREIGN KEY (cycle_id) REFERENCES cycle(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE,
            FOREIGN KEY (edge_id) REFERENCES edge(id)
                ON DELETE CASCADE
                ON UPDATE CASCADE
        );

        """,  # 0
        "SELECT mode FROM graph WHERE id = {id!i:1}",  # 1
        """
        INSERT INTO graph (id, directed, acyclic, metadata, mode)
        VALUES (
            {id!i:1}, {directed!i:2}, {acyclic!i:3}, {metadata!s:4}, {mode!i:5}
        )
        """,  # 2
        """
        SELECT directed, acyclic, metadata, mode, id
        FROM graph
        WHERE id = {id!i:1}
        """,  # 3
        """
        UPDATE graph
        SET
            directed = {directed!i:1},
            acyclic = {acyclic!i:2},
            metadata = {metadata!s:3},
            mode = {mode!i:4}
        WHERE id = {id!i:5}
        """,  # 4
        "DELETE FROM graph WHERE id = {id!i:1}",  # 5
        "SELECT COALESCE(MAX(id), -1) + 1 FROM vertex",  # 6
        """
        INSERT INTO vertex (
            id,
            predecessor,
            graph_id,
            aux_id,
            bf_distance,
            pushed,
            popped,
            tree,
            color,
            metadata,
            sp_estimate,
            topological_id,
            scc_index,
            scc_lowlink,
            scc_onstack,
            mst_key
        )
        VALUES (
            {id!i:1},
            {predecessor!i:2},
            {graph_id!s:3},
            {aux_id!s:4},
            {bf_distance!i:5},
            {pushed!i:6},
            {popped!i:7},
            {tree!i:8},
            {color!i:9},
            {metadata!s:10},
            {sp_estimate!f:11},
            {topological_id!i:12},
            {scc_index!i:13},
            {scc_lowlink!i:14},
            {scc_onstack!i:15},
            {mst_key!f:16}
        )
        RETURNING id
        """,  # 7
        "SELECT * FROM vertex WHERE id = {id!i:1}",  # 8
        """
        UPDATE
            vertex
        SET
            predecessor = {predecessor!i:1},
            graph_id = {graph_id!s:2},
            aux_id = {aux_id!s:3},
            bf_distance = {bf_distance!i:4},
            pushed = {pushed!i:5},
            popped = {popped!i:6},
            tree = {tree!i:7},
            color = {color!i:8},
            metadata = {metadata!s:9},
            sp_estimate = {sp_estimate!f:10},
            topological_id = {topological_id!i:11},
            scc_index = {scc_index!i:12},
            scc_lowlink = {scc_lowlink!i:13},
            scc_onstack = {scc_onstack!i:14},
            mst_key = {mst_key!f:15}
        WHERE
            id = {id!i:16}
        """,  # 9
        "DELETE FROM vertex WHERE id = {id!i:1}",  # 10
        "SELECT COALESCE(MAX(id), -1) + 1 FROM edge",  # 11
        """
        INSERT INTO edge (
            id,
            transpose_id,
            predecessor,
            parent_vertex_id,
            child_vertex_id,
            graph_id,
            type,
            tree,
            color,
            pushed,
            popped,
            component_graph_bridge,
            metadata,
            weight,
            aux_id,
            mf_capacity,
            mf_flow
        )
        VALUES (
            {id!i:1},
            {transpose_id!i:2},
            {predecessor!i:3},
            {parent_vertex_id!i:4},
            {child_vertex_id!i:5},
            {graph_id!s:6},
            {type!i:7},
            {tree!i:8},
            {color!i:9},
            {pushed!i:10},
            {popped!i:11},
            {component_graph_bridge!i:12},
            {metadata!s:13},
            {weight!f:14},
            {aux_id!s:15},
            {mf_capacity!f:16},
            {mf_flow!f:17}
        )
        RETURNING id
        """,  # 12
        "SELECT * FROM edge WHERE id = {id!i:1}",  # 13
        """
        UPDATE
            edge
        SET
            transpose_id = {transpose_id!i:1},
            predecessor = {predecessor!i:2},
            parent_vertex_id = {parent_vertex_id!i:3},
            child_vertex_id = {child_vertex_id!i:4},
            graph_id = {graph_id!s:5},
            type = {type!i:6},
            tree = {tree!i:7},
            color = {color!i:8},
            pushed = {pushed!i:9},
            popped = {popped!i:10},
            component_graph_bridge = {component_graph_bridge!i:11},
            metadata = {metadata!s:12},
            weight = {weight!f:13},
            aux_id = {aux_id!s:14},
            mf_capacity = {mf_capacity!f:15},
            mf_flow = {mf_flow!f:16}

        WHERE
            id = {id!i:15}
        """,  # 14
        "DELETE FROM edge WHERE id = {id!i:1}",  # 15
        """
        INSERT INTO graph (id, acyclic, directed, metadata)
        VALUES (
            {id!i:1},
            (SELECT acyclic FROM graph WHERE id = {id!i:2}),
            (SELECT directed FROM graph WHERE id = {id!i:3}), 
            {metadata!s:4}
        )
        """,  # 16
        "SELECT id FROM vertex WHERE graph_id = {graph_id!s:1}",  # 17
        """
        SELECT
            id, parent_vertex_id, child_vertex_id, component_graph_bridge
        FROM
            edge
        WHERE
            graph_id = {graph_id!s:1}
        """,  # 18
        "UPDATE edge SET transpose_id = {transpose_id!i:1} WHERE id = {id!i:2}",  # 19
        """
        UPDATE edge
        SET tree = NULL, color = 0, pushed = NULL, popped = NULL
        WHERE graph_id = {graph_id!s:1}
        """,  # 20
        "SELECT id FROM edge WHERE graph_id = {graph_id!s:1}",  # 21
        """
        UPDATE
            edge
        SET
            color = 1, pushed = {pushed!i:1}, tree = {tree!i:2}
        WHERE
            graph_id = {graph_id!s:3} AND id = {id!i:4} AND color = 0
        RETURNING
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        """,  # 22
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            graph_id = {graph_id!s:1}
            AND parent_vertex_id = {parent_vertex_id!i:2}
        """,  # 23
        """
        SELECT COUNT(*)
        FROM edge
        WHERE graph_id = {graph!s:1} AND tree = {tree!i:2} AND color = 1
        """,  # 24
        """
        UPDATE edge
        SET color = 1, pushed = {pushed!i:1}, tree = {tree!i:2}
        WHERE id = {id!i:3}
        """,  # 25
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            graph_id = {graph_id!s:1}
            AND parent_vertex_id = {parent_vertex_id!i:2}
        """,  # 26
        "UPDATE edge SET color = 2, popped = {popped!i:1} WHERE id = {id!i:2}",  # 27
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            graph_id = {graph_id!s:1}
            AND pushed = (
                SELECT
                    MAX(pushed)
                FROM
                    edge
                WHERE
                    graph_id = {graph_id!s:2}
                    AND tree = {tree!i:3}
                    AND color = 1
                    AND child_vertex_id = {child_vertex_id!i:4}
                LIMIT 1
            )
        """,  # 28
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            graph_id = {graph_id!s:1}
            AND parent_vertex_id = {parent_vertex_id!i:2}
        """,  # 29
        "DELETE FROM cycle WHERE graph_id = {graph!s:1}",  # 30
        "SELECT cycle_id FROM cycle_edge WHERE edge_id = {edge_id!i:1} LIMIT 1",  # 31
        """
        SELECT id
        FROM edge
        WHERE
            pushed >= {pushed1!i:1}
            AND pushed <= {pushed2!i:2}
            AND color = 1
            AND tree = {tree!i:3}
            AND graph_id = {graph_id!s:4}
        """,  # 32
        """
        INSERT INTO cycle (id, graph_id, cardinality)
        VALUES (
            COALESCE((SELECT MAX(id) FROM cycle), -1) + 1,
            {graph_id!s:1},
            {cardinality!i:2}
        )
        RETURNING id
        """,  # 33
        """
        INSERT INTO cycle_edge (cycle_id, edge_id)
        VALUES ({cycle_id!i:1}, {edge_id!i:2})
        """,  # 34
        """
        SELECT cycle_id
        FROM cycle_edge
        WHERE edge_id = {edge_id!i:1} LIMIT 1
        """,  # 35
        """
        SELECT
            e.id,
            e.child_vertex_id,
            e.parent_vertex_id,
            e.tree,
            e.color,
            e.pushed,
            e.graph_id
        FROM
            cycle_edge AS ce
        LEFT JOIN
            edge AS e
            ON e.id = ce.edge_id
        WHERE
            ce.cycle_id = {cycle_id!i:1} AND e.pushed = e.popped - 1
        """,  # 36
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            parent_vertex_id = {parent_vertex_id!i:1} AND color = 1
        """,  # 37
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            child_vertex_id = {child_vertex_id!i:1}
            AND color = 1
            AND pushed = (SELECT MAX(pushed) FROM edge)
        """,  # 38
        """
        SELECT
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        FROM
            edge
        WHERE
            color = 1
            AND child_vertex_id = (
                SELECT e.parent_vertex_id
                FROM edge AS e
                INNER JOIN cycle_edge AS ce
                    ON ce.edge_id = e.id
                WHERE
                    e.graph_id = {graph_id!s:1}
                    AND e.tree = {tree!i:2}
                    AND e.color = 2
                    AND e.pushed <= {pushed1!i:3}
                    AND e.pushed >= {pushed2!i:4}
                    AND ce.cycle_id = {cycle_id!i:5}
            )
        """,  # 39
        """
        SELECT
            id
        FROM
            edge
        WHERE
            (
                pushed BETWEEN {pushed1!i:1} AND {pushed2!i:2}
                OR pushed BETWEEN {pushed3!i:3} AND {pushed4!i:4}
                OR pushed BETWEEN (
                    SELECT pushed
                    FROM edge
                    WHERE
                        parent_vertex_id = {parent_vertex_id!i:5}
                        AND pushed = (
                            SELECT MAX(pushed)
                            FROM edge
                            WHERE parent_vertex_id = {parent_vertex_id!i:6}
                        )
                ) AND {pushed5!i:7}
            )
            AND tree = {tree!i:8}
            AND graph_id = {graph_id!s:9}
        """,  # 40
        """
        INSERT INTO cycle (id, graph_id, cardinality)
        VALUES (
            COALESCE((SELECT MAX(id) FROM cycle), -1) + 1,
            {graph_id!s:1},
            {cardinality!i:2}
        )
        RETURNING id
        """,  # 41
        """
        INSERT INTO cycle_edge (cycle_id, edge_id)
        VALUES ({cycle_id!i:1}, {edge_id!i:2})
        """,  # 42
        "UPDATE graph SET acyclic = 1 WHERE id = {id!i:1}",  # 43
        "SELECT COUNT(*) FROM cycle WHERE graph_id = {graph_id!s:1}",  # 44
        "UPDATE vertex SET topological_id = NULL WHERE graph_id = {graph_id!s:1}",  # 45
        """
        UPDATE
            vertex
        SET
            topological_id = COALESCE(
                (
                    SELECT MAX(topological_id) + 1
                    FROM vertex
                    WHERE graph_id = {graph_id!s:1}
                ),
                COALESCE(
                    (
                        SELECT topological_id
                        FROM vertex
                        WHERE id = {id!i:2}
                    ),
                    0
                )
            )
        WHERE
            id = {id!i:3}
        """,  # 46
        """
        SELECT id
        FROM vertex
        WHERE graph_id = {graph_id!s:1}
        ORDER BY topological_id DESC
        """,  # 47
        """
        UPDATE vertex
        SET topological_id = {topological_id!i:1}
        WHERE id = {id!i:2}
        """,  # 48
        """
        UPDATE vertex
        SET scc_index = NULL, scc_lowlink = NULL, scc_onstack = 0
        WHERE graph_id = {graph_id!s:1}
        """,  # 49
        """
        UPDATE
            vertex
        SET
            scc_index = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex), -1
            ),
            scc_lowlink = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex), -1
            ),
            scc_onstack = 1
        WHERE
            id = {id!i:1} AND scc_index IS NULL
        """,  # 50
        """
        UPDATE
            vertex
        SET
            scc_index = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex), -1
            ),
            scc_lowlink = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex), -1
            ),
            scc_onstack = 1
        WHERE
            id = {id!i:1} AND scc_index IS NULL
        RETURNING id, scc_index, scc_lowlink, scc_onstack
        """,  # 51
        """
        SELECT id, scc_index, scc_lowlink, scc_onstack
        FROM vertex
        WHERE id = {id!i:1}
        """,  # 52
        """
        SELECT id, scc_index, scc_lowlink, scc_onstack
        FROM vertex
        WHERE id = {id!i:1}
        """,  # 53
        "UPDATE vertex SET scc_lowlink = {scc_lowlink!i:1} WHERE id = {id!i:2}",  # 54
        """
        SELECT id, scc_index, scc_lowlink, scc_onstack
        FROM vertex
        WHERE id = {id!i:1}
        """,  # 55
        """
        SELECT id, scc_index, scc_lowlink, scc_onstack
        FROM vertex
        WHERE id = {id!i:1}
        """,  # 56
        "UPDATE vertex SET scc_lowlink = {scc_lowlink!i:1} WHERE id = {id!i:2}",  # 57
        "UPDATE vertex SET scc_onstack = 0 WHERE scc_lowlink = {scc_lowlink!i:1}",  # 58
        "UPDATE vertex SET scc_onstack = 0 WHERE id = {id!i:1}",  # 59
        """
        UPDATE edge
        SET predecessor = NULL, pushed = NULL
        WHERE graph_id = {graph_id!s:1}
        """,  # 60
        "UPDATE edge SET pushed = 1 WHERE id = {id!i:1}",  # 61
        """
        SELECT COUNT(*)
        FROM edge
        WHERE graph_id = {graph_id!s:1} AND pushed > 0
        """,  # 62
        """
        SELECT id, predecessor, pushed
        FROM edge
        WHERE graph_id = {graph_id!s:1} AND pushed > 0
        ORDER BY pushed ASC
        LIMIT 1
        """,  # 63
        "UPDATE edge SET pushed = -1 * pushed WHERE id = {id!i:1}",  # 64
        """
        WITH
            w AS (
                SELECT id, predecessor, pushed, child_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND parent_vertex_id = (
                    SELECT child_vertex_id FROM edge WHERE id = {id!i:1}
                )
            ),
            y AS (
                SELECT id, predecessor, pushed, parent_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND child_vertex_id = (
                    SELECT child_vertex_id FROM edge WHERE id = {id!i:2}
                )
            ),
            x AS (
                SELECT id, predecessor, pushed, child_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND parent_vertex_id = (
                    SELECT parent_vertex_id FROM edge WHERE id = {id!i:3}
                )
            ),
            z AS (
                SELECT id, predecessor, pushed, parent_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND child_vertex_id = (
                    SELECT parent_vertex_id FROM edge WHERE id = {id!i:4}
                )
            ),
            a AS (
                SELECT *
                FROM (SELECT * FROM w UNION SELECT * FROM y)
                WHERE v NOT IN (
                    SELECT child_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> {id!i:5}
                    UNION
                    SELECT parent_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> {id!i:6}
                )
            ),
            b AS (
                SELECT *
                FROM (SELECT * FROM x UNION SELECT * FROM z)
                WHERE v NOT IN (
                    SELECT child_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> {id!i:7}
                    UNION
                    SELECT parent_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> {id!i:8}
                )
            )
            SELECT id, predecessor, pushed
            FROM (SELECT * FROM a UNION SELECT * FROM b)
            WHERE id NOT IN (
                SELECT a.id FROM a INNER JOIN b ON a.v = b.v
            )
        """,  # 65
        """
        UPDATE edge
        SET predecessor = {predecessor!i:1}, pushed = (
            SELECT COALESCE(MAX(pushed), 1) + 1
            FROM edge
            WHERE graph_id = {graph_id!s:2} AND pushed > 0
        )
        WHERE id = {id!i:3}
        """,  # 66
        "UPDATE edge SET pushed = NULL WHERE graph_id = {graph_id!s:1}",  # 67
        """
        SELECT id, predecessor, NULL AS pushed
        FROM edge
        WHERE id = {id!i:1}
        """,  # 68
        """
        UPDATE vertex
        SET mst_key = {mst_key!f:1}, predecessor = NULL, color = 0
        WHERE graph_id = {graph_id!s:2}
        """,  # 69
        "UPDATE vertex SET mst_key = 0, color = 0 WHERE id = {id!i:1}",  # 70
        """
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = {graph_id!s:1} AND color = 0
        """,  # 71
        """
        SELECT id, predecessor, mst_key, color
        FROM vertex
        WHERE graph_id = {graph_id!s:1} AND color = 0
        ORDER BY mst_key ASC
        LIMIT 1
        """,  # 72
        """
        UPDATE vertex
        SET color = 2
        WHERE graph_id = {graph_id!s:1} AND id = {id!i:2}
        """,  # 73
        """
        WITH
            x AS (
                SELECT parent_vertex_id AS id
                FROM edge
                WHERE graph_id = {graph_id!s:1} AND child_vertex_id = {child_vertex_id!i:2}
            ),
            y AS (
                SELECT child_vertex_id AS id
                FROM edge
                WHERE graph_id = {graph_id!s:3} AND parent_vertex_id = {parent_vertex_id!i:4}
            )
        SELECT id, predecessor, mst_key, color
        FROM vertex
        WHERE graph_id = {graph_id!s:5} AND id IN (
            SELECT id FROM x
            UNION
            SELECT id FROM y
        )
        """,  # 74
        """
        SELECT weight
        FROM edge
        WHERE 
            graph_id = {graph_id!s:1}
            AND (
                (parent_vertex_id = {vid1!i:2} AND child_vertex_id = {vid2!i:3})
                OR (child_vertex_id = {vid1!i:4} AND parent_vertex_id = {vid2!i:5})
            )
        ORDER BY weight ASC
        LIMIT 1
        """,  # 75
        """
        UPDATE vertex
        SET predecessor = {predecessor!i:1}, mst_key = {mst_key!f:2}
        WHERE id = {id!i:3}
        """,  # 76
        """
        SELECT id, predecessor, mst_key, color
        FROM vertex
        WHERE id = {id!i:1}
        """,  # 77
        """
        UPDATE vertex
        SET sp_estimate = {sp_estimate!i:1}, predecessor = NULL, color = 0
        WHERE graph_id = {graph_id!s:2}
        """,  # 78
        "UPDATE vertex SET sp_estimate = 0, color = 0 WHERE id = {id!i:1}",  # 79
        """
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = {graph_id!s:1} AND color = 0
        """,  # 80
        """
        SELECT id, predecessor, sp_estimate, color
        FROM vertex
        WHERE graph_id = {graph_id!s:1} AND color = 0
        ORDER BY sp_estimate ASC
        LIMIT 1
        """,  # 81
        """
        UPDATE vertex
        SET color = 2
        WHERE graph_id = {graph_id!s:1} AND id = {id!i:2}
        """,  # 82
        """
        SELECT
            v.id, v.predecessor, v.sp_estimate, v.color
        FROM
            edge AS e
        INNER JOIN
            vertex AS v
            ON v.id = e.child_vertex_id
        WHERE
            v.graph_id = {graph_id!s:1}
            AND e.parent_vertex_id = {parent_vertex_id!i:2}
        """,  # 83
        """
        SELECT weight
        FROM edge
        WHERE 
            graph_id = {graph_id!s:1}
            AND (
                parent_vertex_id = {parent_vertex_id!i:2}
                AND child_vertex_id = {child_vertex_id!i:3}
            )
        """,  # 84
        """
        UPDATE vertex
        SET predecessor = {predecessor!i:1}, sp_estimate = {sp_estimate!f:2}
        WHERE id = {id!i:3}
        """,  # 85
        """
        SELECT id, predecessor, sp_estimate, color
        FROM vertex
        WHERE id = {id!i:1}
        """,  # 86
    ]

    model = sql[0]

    def __init__(self, connection: object) -> None:
        """
        :param connection: a PEP-249 compliant database connection

        :return None:
        """

        # bind connection and cursor
        self.connection = connection
        self.cursor = self.connection.cursor()

        # format sql according to connection's paramstyle
        formatter = string.Formatter()
        param_style = sys.modules[connection.__module__].paramstyle
        for i, statement in enumerate(self.sql):
            statement_fragments = []
            for tup in formatter.parse(statement):
                statement_fragments.append(tup[0])
                if tup[1] is None:
                    continue
                if param_style == "qmark":
                    statement_fragments.append("?")
                elif param_style == "numeric":
                    statement_fragments.append(":" + tup[2])
                elif param_style == "named":
                    statement_fragments.append(":" + tup[1])
                elif param_style == "format":
                    statement_fragments.append("%" + tup[3])
                elif param_style == "pyformat":
                    statement_fragments.append(f"%({tup[1]}){tup[3]}")
                else:
                    raise Exception(
                        f"bad paramstyle for {connection.__module__.__name__}"
                    )
            self.sql[i] = "".join(statement_fragments)
        self.sql = tuple(self.sql)

    def close(self: object) -> None:
        """Close the cursor then close the connection.

        :return None:
        """
        self.cursor.close()
        self.connection.close()

    def load_schema(self: object) -> None:
        """Execute the model and commit.

        :return None:"""

        # execute all statements in model
        for table_definition in self.sql[0].split(";"):
            _ = self.cursor.execute(table_definition.strip())
        self.connection.commit()

    def get_ordered_dict_record(
        self: object, dql: str, params: object
    ) -> OrderedDict:
        """Fetch one record and return it as an ordered dictionary.

        :param dql: a select-statement that returns one record
        :param params: parameters to interpolate into ``dql``

        :return collections.OrderedDict:
        """
        cursor = self.cursor.execute(dql, params)
        columns = tuple(col[0] for col in cursor.description)
        return OrderedDict((item for item in zip(columns, cursor.fetchone())))

    def check_mode(self: object, graph: str, *flags: list) -> bool:
        """Determine if any of the given "mutability mode" flags are
        set for the graph.

        :param graph: name of the graph to check
        :param flags: zero or more mode flags to check

        :return bool:
        """

        # fetch the mode of graph
        mode = self.cursor.execute(self.sql[1], (graph,)).fetchone()

        # raise if bad mode
        if mode is None or not isinstance(mode[0], int):
            raise Exception(f"graph '{graph}' has bad mode")

        # return true if any in flags is set in mode else false
        if any((mode[0] & f) >> int(math.log2(f)) for f in flags):
            return True
        return False

    def create_graph(
        self: object,
        name: str,
        directed: bool | int,
        acyclic: bool | int = None,
        mode: int = 0,
        **metadata,
    ) -> None:
        """Create a graph. Optional keyword arguments are serialized as a JSON object and stored as metadata for the graph.

        :param name: name of the graph to create
        :param directed: whether the graph is directed (1) or undirected (0)
        :param acyclic: whether the graph is acyclic (1) or not (0)
        :param mode: mutability mode flags to set for the graph
        :param metadata: any additional metadata to associate with the graph

        :return None:
        """

        # possibly serialize metadata params as a json object
        if metadata:
            metadata = json.dumps(metadata)
        else:
            metadata = None

        # create the graph
        self.cursor.execute(
            self.sql[2], (name, directed, acyclic, metadata, mode)
        )
        self.connection.commit()

    def alter_graph(self: object, name: str, **attributes) -> None:
        """Update attributes of a graph with any keyword arguments. Raise ``Exception`` if any keyword is not a valid graph attribute or if no attributes are provided.

        :param name: name of the graph to update
        :param attributes: graph attributes to update with

        :return None:"""

        # raise if called with nothing to alter with
        if not attributes:
            raise Exception(f"no attributes provided to update '{name}'")

        # fetch current record and update it
        record = self.get_ordered_dict_record(self.sql[3], (name,))
        for attribute in attributes:
            if attribute in record:
                record[attribute] = attributes[attribute]
            else:
                raise Exception(f"attribute '{attribute}' not part of graph")

        # dump metadata if it's a dictionary
        if record.get("metadata") is not None:
            record["metadata"] = json.dumps(record["metadata"])

        # udpate
        self.cursor.execute(self.sql[4], tuple(record.values()))
        self.connection.commit()

    def delete_graphs(self: object, *names: list[str]) -> None:
        """Delete graphs with the given names.

        :param names: names of the graphs to delete

        :return None:
        """
        self.cursor.executemany(self.sql[5], ((n,) for n in names))
        self.connection.commit()

    def add_vertices(
        self: object, graph: str, *vertices: list[dict]
    ) -> list[int]:
        """Add vertices to graph ``graph``. If a vertex has a "metadata" key, assume the corresponding value is a dictionary and dump it as a JSON object using ``json.dumps``. Raise ``Exception`` if a vertex has keys that are not valid vertex attributes. Return a list of ids for the created vertices.

        :param graph: name of the graph to add vertices to
        :param vertices: one or more dictionaries containing vertex attributes

        :return list[int]:
        """

        next_id = self.cursor.execute(self.sql[6]).fetchone()[0]

        # format vertex dicts
        new_ids = []
        for i, vertex in enumerate(vertices):

            # fetch a template vertex dictionary
            vertex_template = vertex_odict_factory()

            # raise if bad vertex attrs
            if set(vertex) - set(vertex_template):
                raise Exception("bad vertex attributes")

            vertex_template["graph_id"] = graph

            # dump metadata
            if vertices[i].get("metadata") is not None:
                vertex_template["metadata"] = json.dumps(
                    vertices[i].pop("metadata")
                )

            # fill in any missing columns
            for attr in vertex:
                vertex_template[attr] = vertices[i][attr]

            if vertex_template["id"] is None:
                vertex_template["id"] = next_id
                next_id += 1

            # add the vertex
            new_ids.append(
                self.cursor.execute(
                    self.sql[7], tuple(vertex_template.values())
                ).fetchone()[0]
            )
        self.connection.commit()

        # return the created vertices
        return new_ids

    def alter_vertex(self: object, vertex_id: str, **attributes) -> None:
        """Update attributes of a vertex with any keyword arguments. Raise ``Exception`` if any keyword is not a valid vertex attribute or if no attributes are provided. Assume a "metadata" keyword argument is a dictionary and dump it as a JSON object using ``json.dumps``.

        :param vertex_id: id of the vertex to update
        :param attributes: vertex attributes to update with

        :return None:
        """

        # raise if called with nothing to alter with
        if not attributes:
            raise Exception(
                f"no attributes provided to update vertex '{vertex_id}'"
            )

        # fetch current record and update it
        record = self.get_ordered_dict_record(self.sql[8], (vertex_id,))
        for attribute in attributes:
            if attribute in record:
                record[attribute] = attributes[attribute]
            else:
                raise Exception(f"attribute '{attribute}' not part of vertex")

        # dump metadata if it's not a string
        if record["metadata"] is not None:
            record["metadata"] = json.dumps(record["metadata"])

        # add add a second time for use in where clause
        where_param = record.pop("id")

        # udpate
        self.cursor.execute(self.sql[9], (*record.values(), where_param))
        self.connection.commit()

    def delete_vertices(self: object, *ids: list[str]) -> None:
        """Delete vertices with the given ids.

        :param ids: ids of the vertices to delete

        :return None:"""
        self.cursor.executemany(self.sql[10], ((i,) for i in ids))
        self.connection.commit()

    def add_edges(self: object, graph: str, *edges: list[dict]) -> list[int]:
        """Add edges to graph ``graph``. If an edge has a "metadata" key, assume the corresponding value is a dictionary and dump it as a JSON object using ``json.dumps``. Raise ``Exception`` if an edge has keys that are not valid edge attributes. Return a list of ids for the created edges.

        :param graph: name of the graph to add edges to
        :param edges: one or more dictionaries containing edge attributes

        :return list[int]:"""

        next_id = self.cursor.execute(self.sql[11]).fetchone()[0]

        # format vertex dicts
        new_ids = []
        for i, vertex in enumerate(edges):

            # fetch a template vertex dictionary
            edge_template = edge_odict_factory()

            # raise if bad vertex attrs
            if set(vertex) - set(edge_template):
                raise Exception("bad edge attributes")

            edge_template["graph_id"] = graph

            # dump metadata
            if edges[i].get("metadata") is not None:
                edge_template["metadata"] = json.dumps(
                    edges[i].pop("metadata")
                )

            # fill in any missing columns
            for attr in vertex:
                edge_template[attr] = edges[i][attr]

            if edge_template["id"] is None:
                edge_template["id"] = next_id
                next_id += 1

            # add the vertex
            new_ids.append(
                self.cursor.execute(
                    self.sql[12], tuple(edge_template.values())
                ).fetchone()[0]
            )
        self.connection.commit()

        # return the created vertices
        return new_ids

    def alter_edge(self: object, edge_id: str, **attributes) -> None:
        """Update attributes of an edge with any keyword arguments. Raise ``Exception`` if any keyword is not a valid edge attribute or if no attributes are provided. Assume a "metadata" keyword argument is a dictionary and dump it as a JSON object using ``json.dumps``.

        :param edge_id: id of the edge to update
        :param attributes: edge attributes to update with

        :return None:
        """

        # raise if called with nothing to alter with
        if not attributes:
            raise Exception(
                f"no attributes provided to update edge '{edge_id}'"
            )

        # fetch current record and update it
        record = self.get_ordered_dict_record(self.sql[13], (edge_id,))
        for attribute in attributes:
            if attribute in record:
                record[attribute] = attributes[attribute]
            else:
                raise Exception(f"attribute '{attribute}' not part of edge")

        # dump metadata if it's not a string
        if record["metadata"] is not None:
            record["metadata"] = json.dumps(record["metadata"])

        # add add a second time for use in where clause
        where_param = record.pop("id")

        # udpate
        self.cursor.execute(self.sql[14], (*record.values(), where_param))
        self.connection.commit()

    def delete_edges(self: object, *ids: list[str]) -> None:
        """Delete edges with the given ids.

        :param ids: ids of the edges to delete

        :return None:"""
        self.cursor.executemany(self.sql[15], ((i,) for i in ids))

    def create_frucht(self: object, name: str) -> None:
        """Create a directed graph with Frucht vertex-edge structure.

        :param name: name of the graph to create

        :return None:"""
        self.create_graph(name, 1)
        _ = self.add_vertices(name, *[{"metadata": {}} for _ in range(12)])
        _ = self.add_edges(
            name,
            {"parent_vertex_id": _[0], "child_vertex_id": _[10]},
            {"parent_vertex_id": _[10], "child_vertex_id": _[11]},
            {"parent_vertex_id": _[11], "child_vertex_id": _[8]},
            {"parent_vertex_id": _[8], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[3], "child_vertex_id": _[0]},
            {"parent_vertex_id": _[0], "child_vertex_id": _[1]},
            {"parent_vertex_id": _[9], "child_vertex_id": _[10]},
            {"parent_vertex_id": _[11], "child_vertex_id": _[9]},
            {"parent_vertex_id": _[8], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[4], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[2], "child_vertex_id": _[3]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[2]},
            {"parent_vertex_id": _[1], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[7], "child_vertex_id": _[5]},
            {"parent_vertex_id": _[5], "child_vertex_id": _[9]},
        )

    def create_peterson(self: object, name: str) -> None:
        """Create a directed graph with Peterson vertex-edge structure.

        :param name: name of the graph to create

        :return None:"""
        self.create_graph(name, 1, 0)
        _ = self.add_vertices(name, *[{"metadata": {}} for _ in range(10)])
        _ = self.add_edges(
            name,
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
            {"parent_vertex_id": _[5], "child_vertex_id": _[6]},
            {"parent_vertex_id": _[6], "child_vertex_id": _[7]},
            {"parent_vertex_id": _[7], "child_vertex_id": _[8]},
            {"parent_vertex_id": _[8], "child_vertex_id": _[9]},
            {"parent_vertex_id": _[9], "child_vertex_id": _[5]},
        )

    def transpose(
        self: object,
        graph: str,
        transposed_name: str = None,
        chunk_size: int = 250,
    ) -> str:
        """Reverse the direction of all edges in a directed graph. Raise ``Exception`` if the graph's edges are immutable.

        :param graph: name of the graph to transpose
        :param transposed_name: name of the transposed graph to create (default is ``graph + "_transpose"``)
        :param chunk_size: number of edges to process at a time

        :return str: the name of the transposed graph
        """

        # check for immutability flags set
        if self.check_mode(graph, EDIM):
            raise Exception(f"cannot alter edges of '{graph}'")

        # possibly build a transposed name
        if transposed_name is None:
            transposed_name = graph + "_transpose"

        # create a graph record for transposed
        self.cursor.execute(
            self.sql[16],
            (transposed_name, graph, graph, json.dumps({"graph": graph})),
        )

        # clone vertices with chunked pattern
        push_cursor = self.connection.execute(self.sql[17], (graph,))
        while chunk := push_cursor.fetchmany(size=chunk_size):

            # store G's vertex id in metadata
            _ = self.add_vertices(
                transposed_name,
                *[
                    {"metadata": {"graph": graph, "vertex": v[0]}}
                    for v in chunk
                ],
            )

        # clone edges with chunked pattern
        push_cursor = push_cursor.execute(self.sql[18], (graph,))
        while chunk := push_cursor.fetchmany(size=chunk_size):

            # swaps child/parent vertex ids
            transpose_edge_ids = self.add_edges(
                transposed_name,
                *[
                    {
                        "parent_vertex_id": e[2],
                        "child_vertex_id": e[1],
                        "component_graph_bridge": e[3],
                        "metadata": {"graph": graph, "edge": e[0]},
                    }
                    for e in chunk
                ],
            )

            self.cursor.executemany(
                self.sql[19], zip(transpose_edge_ids, (e[0] for e in chunk))
            )

        # clean up
        self.connection.commit()
        push_cursor.close()
        return transposed_name

    def df_search(self: object, graph: str, **hooks: dict) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
            raise Exception(
                f"cannot alter vertices/edges/cycles/cycle edges of '{graph}'"
            )

        # run enter hook
        hooks.get("enter", lambda y, z: None)(graph, self.cursor)

        # initialization
        current_time = 0
        self.cursor.execute(self.sql[20], (graph,))

        # edge ids can be used as a tree ids
        trees_cursor = self.connection.execute(self.sql[21], (graph,))
        while (tree := trees_cursor.fetchone()) is not None:
            tree = tree[0]

            # push this tree's first edge
            hooks.get("before_push", lambda x, y, z: None)(
                None, None, self.cursor
            )
            edge = self.cursor.execute(
                self.sql[22], (current_time, tree, graph, tree)
            ).fetchone()

            # edge with id 'tree' was not white
            if edge is None:
                continue

            # fetch edges growing off current edge
            branch_tips = self.cursor.execute(
                self.sql[23], (graph, edge[1])
            ).fetchall()

            # compute stack height to use below as break condition
            tree_size = self.cursor.execute(
                self.sql[24], (graph, tree)
            ).fetchone()[0]

            # new tree created, trigger hook
            hooks.get("new_tree", lambda w, x, y, z: None)(
                tree_size, edge, branch_tips, self.cursor
            )

            # edge pushed, trigger hook and increment current time
            hooks.get("after_push", lambda x, y, z: None)(
                edge, branch_tips, self.cursor
            )
            current_time += 1

            # while the stack is not empty
            while tree_size > 0:

                # handle any possible cycles
                hooks.get("find_cycles", lambda v, w, x, y, z: None)(
                    tree, current_time, edge, branch_tips, self.cursor
                )

                # found an edge to push
                if Color.white in (e[4] for e in branch_tips):

                    # depth first doesn't care which edge to pick
                    edge = next(
                        filter(lambda e: e[4] == Color.white, branch_tips)
                    )

                    # push this edge
                    hooks.get("before_push", lambda x, y, z: None)(
                        edge, branch_tips, self.cursor
                    )
                    self.cursor.execute(
                        self.sql[25], (current_time, tree, edge[0])
                    )

                    # fetch edges growing off current edge
                    branch_tips = self.cursor.execute(
                        self.sql[26], (graph, edge[1])
                    ).fetchall()
                    hooks.get("after_push", lambda x, y, z: None)(
                        edge, branch_tips, self.cursor
                    )
                    current_time += 1
                    tree_size += 1

                    # don't enter pop loop
                    continue

                # no more edges to push, do a pop loop
                while Color.white not in (t[4] for t in branch_tips):

                    # pop the edge
                    hooks.get("before_pop", lambda x, y, z: None)(
                        edge, branch_tips, self.cursor
                    )
                    self.cursor.execute(self.sql[27], (current_time, edge[0]))
                    current_time += 1
                    tree_size -= 1

                    # leave pop loop if stack is empty
                    if tree_size == 0:
                        break

                    # set edge to new stack top
                    edge = self.cursor.execute(
                        self.sql[28], (graph, graph, tree, edge[2])
                    ).fetchone()

                    # ask stack top for its branch tips
                    branch_tips = self.cursor.execute(
                        self.sql[29], (graph, edge[1])
                    ).fetchall()
                    hooks.get("after_pop", lambda x, y, z: None)(
                        edge, branch_tips, self.cursor
                    )

                # run return hook
                if hooks.get("return_early", lambda y, z: False)(
                    graph, self.cursor
                ):
                    self.connection.commit()
                    trees_cursor.close()
                    return

        # commit changes and exit
        self.connection.commit()
        trees_cursor.close()
        hooks.get("exit", lambda y, z: None)(graph, self.cursor)

    def find_cycles(self: object, graph: str) -> None:
        """"""

        if self.check_mode(graph, CYIM, CEIM):
            raise Exception(f"cannot alter cycles of '{graph}'")

        # delete existing cycles
        self.cursor.execute(self.sql[30], (graph,))

        def cycles_handler(
            tree: int,
            current_time: int,
            edge: tuple,
            branch_tips: list[tuple],
            cursor: object,
        ) -> None:
            """"""

            # flag to know if must update graph.acyclic
            update_graph_table = False

            # current graph
            graph_id = edge[6]

            # edge's cycle if any
            edge_cycle_id = cursor.execute(self.sql[31], (edge[0],)).fetchone()
            if edge_cycle_id is not None:
                edge_cycle_id = edge_cycle_id[0]

            # for each gray-bump cycle found
            for bt in (e for e in branch_tips if e[4] == 1):

                # fetch the edge ids of the cycle
                cycle_edge_ids = cursor.execute(
                    self.sql[32], (bt[5], current_time, tree, graph_id)
                ).fetchall()

                # compute the cycle length
                cardinality = len(cycle_edge_ids)

                # create a cycle record and return its id
                cycle_id = cursor.execute(
                    self.sql[33], (graph_id, cardinality)
                ).fetchone()[0]

                # and use cycle_id and cycle_edge_ids to create cycle_edge
                # records
                cursor.executemany(
                    self.sql[34],
                    [(cycle_id, edge_id[0]) for edge_id in cycle_edge_ids],
                )

                # and set update graph falg to true
                update_graph_table = True

            # for each edge, D, that a new cycle was closed on
            black_tips = tuple(
                e for e in branch_tips if e[4] == Color.black and e[3] == tree
            )
            for D in black_tips:

                # continue if D is part of a different tree
                if D[3] != tree:
                    continue

                # fetch piggyback cycle id
                _ = cursor.execute(self.sql[35], (D[0],)).fetchone()

                # continue if piggyback cycle doesnt exist
                if _ is None:
                    continue

                # set piggyback cycle id
                piggyback_cycle_id = _[0]

                # continue if piggyback cycle is edge's cycle
                if piggyback_cycle_id == edge_cycle_id:
                    continue

                # fetch E, edge that closed piggyback cycle
                E = cursor.execute(
                    self.sql[36], (piggyback_cycle_id,)
                ).fetchone()

                if E is None:
                    continue

                # fetch A, edge that E closed piggyback cycle on
                A = cursor.execute(self.sql[37], (E[1],)).fetchone()

                if A is None:
                    continue

                # fetch C, edge that closed new cycle onto D
                C = cursor.execute(self.sql[38], (D[2],)).fetchone()

                if C is None:
                    continue

                # fetch B, from which new cycle forks from piggyback
                B = cursor.execute(
                    self.sql[39],
                    (graph_id, tree, C[5], A[5], piggyback_cycle_id),
                ).fetchone()

                if B is None:
                    continue

                # fetch the new cycle edges
                cycle_edges = cursor.execute(
                    self.sql[40],
                    (A[5], B[5], D[5], E[5], B[1], B[1], C[5], tree, graph_id),
                ).fetchall()

                # compute length of cycle
                cardinality = len(cycle_edges)

                # create new cycle record
                cycle_id = cursor.execute(
                    self.sql[41], (graph_id, cardinality)
                ).fetchone()[0]

                # insert new cycle edges
                cursor.executemany(
                    self.sql[42], [(cycle_id, e[0]) for e in cycle_edges]
                )

                # set update graph flag to true
                update_graph_table = True

            # update the graph's acyclic column
            if update_graph_table:
                cursor.execute(self.sql[43], (graph_id,))
            cursor.connection.commit()

        # run the search
        self.df_search(graph, find_cycles=cycles_handler)

    def topological_sort(
        self: object, graph: str, **search_hooks: dict
    ) -> None:
        """"""

        # raise if graph is marked acyclic
        if self.cursor.execute(self.sql[44], (graph,)).fetchone()[0] > 0:
            raise Exception(f"graph '{graph}' is not acyclic")

        # reset topolgical ids of graph
        self.cursor.execute(self.sql[45], (graph,))
        self.connection.commit()

        def before_pop(
            edge: tuple, branch_tips: list[tuple], cursor: object
        ) -> None:
            """"""
            cursor.execute(self.sql[46], (edge[6], edge[2], edge[2]))

        search_hooks["before_pop"] = before_pop
        self.df_search(graph, **search_hooks)

        # reorder vertices so sort is ascending in topological_id
        topological_id = 0
        for vertex in self.cursor.execute(self.sql[47], (graph,)).fetchall():
            self.cursor.execute(self.sql[48], (topological_id, vertex[0]))
            topological_id += 1
        self.connection.commit()

    def strongly_connected_components(self: object, graph: str) -> None:
        """"""

        # initialize vertices
        self.cursor.execute(self.sql[49], (graph,))
        self.connection.commit()

        # new tree hook
        def new_tree(
            tree_size: int,
            edge: tuple,
            branch_tips: list[tuple],
            cursor: object,
        ) -> None:
            """"""

            # initialize scc attributes of the starting vertex
            cursor.execute(self.sql[50], (edge[2],))

        # after push hook
        def after_push(
            edge: tuple, branch_tips: list[tuple], cursor: object
        ) -> None:
            """"""

            # fetch child vertex
            child = cursor.execute(self.sql[51], (edge[1],)).fetchone()
            if child is None:
                child = self.cursor.execute(
                    self.sql[52], (edge[1],)
                ).fetchone()

            # don't interact with other components
            if child[1] != child[2]:
                return

            # fetch parent
            parent = self.cursor.execute(self.sql[53], (edge[2],)).fetchone()

            # parent inherets component's smallest lowlink or its own
            if Color.white not in (t[4] for t in branch_tips):
                self.cursor.execute(
                    self.sql[54], (min(parent[2], child[1]), parent[0])
                )

        # after pop hook
        def before_pop(
            edge: tuple, branch_tips: list[tuple], cursor: object
        ) -> None:
            """"""

            # fetch scc attributes of parent and child vertex
            parent = self.cursor.execute(self.sql[55], (edge[2],)).fetchone()
            child = self.cursor.execute(self.sql[56], (edge[1],)).fetchone()

            # bumped into a component vertex, adjust its lowlink
            if child[3] == 1:
                self.cursor.execute(
                    self.sql[57], (min(parent[2], child[2]), parent[0])
                )

            # pop parent vertex off scc stack
            if child[2] == parent[1]:
                self.cursor.execute(self.sql[58], (parent[1],))
            if not branch_tips:
                self.cursor.execute(self.sql[59], (child[0],))

        self.df_search(
            graph,
            new_tree=new_tree,
            after_push=after_push,
            before_pop=before_pop,
        )

    def bf_base(
        self: object, graph: str, start_obj: tuple, **hooks: dict
    ) -> None:
        """"""

        # bind all hooks to their names
        enter = hooks.get("enter", lambda x, y, z: None)
        loop_condition = hooks.get("loop_condition", lambda x, y: False)
        pop = hooks.get("pop", lambda x, y: tuple())
        adjacency = hooks.get("adjacency", lambda x, y, z: list())
        push = hooks.get("push", lambda w, x, y, z: None)
        iteration_complete = hooks.get(
            "iteration_complete", lambda w, x, y, z: None
        )
        tixe = hooks.get("exit", lambda x, y: None)

        # main routine
        enter(start_obj, graph, self.cursor)
        while loop_condition(graph, self.cursor):
            obj = pop(graph, self.cursor)
            for adjacent_obj in adjacency(obj, graph, self.cursor):
                push(adjacent_obj, obj, graph, self.cursor)
            iteration_complete(adjacent_obj, obj, graph, self.cursor)
        tixe(graph, self.cursor)

    def ebf_search(self: object, graph: str, start_edge_id: int) -> None:
        """"""

        def enter(edge: tuple, graph: str, cursor: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM):
                raise Exception(f"cannot alter vertices/edges of '{graph}'")

            # initialize all edges
            cursor.execute(self.sql[60], (graph,))
            cursor.execute(self.sql[61], (edge[0],))

        def loop_condition(graph: str, cursor: object) -> bool:
            """"""
            return 0 < cursor.execute(self.sql[62], (graph,)).fetchone()[0]

        def pop(graph: str, cursor: object) -> tuple:
            """"""
            next_edge = cursor.execute(self.sql[63], (graph,)).fetchone()
            cursor.execute(self.sql[64], (next_edge[0],))
            return next_edge

        def adjacency(edge: tuple, graph: str, cursor: object) -> list:
            """"""
            return cursor.execute(self.sql[65], 8 * (edge[0],)).fetchall()

        def push(
            adj_edge: tuple, edge: tuple, graph: str, cursor: object
        ) -> None:
            """"""
            cursor.execute(self.sql[66], (edge[0], graph, adj_edge[0]))

        def tixe(graph: str, cursor: object) -> None:
            """"""
            cursor.execute(self.sql[67], (graph,))

        # fetch start edge data
        start_edge = self.cursor.execute(
            self.sql[68], (start_edge_id,)
        ).fetchone()
        if start_edge is None:
            raise Exception(f"edge '{start_edge_id}' does not exist")

        self.bf_base(
            graph,
            start_edge,
            enter=enter,
            loop_condition=loop_condition,
            pop=pop,
            adjacency=adjacency,
            push=push,
            exit=tixe,
        )

    def minimum_spanning_tree(
        self: object, graph: str, start_vertex_id: int
    ) -> None:
        """"""

        def enter(vertex: tuple, graph: str, cursor: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
                raise Exception(
                    f"cannot alter vertices/edges/cycles of '{graph}'"
                )

            # initialize all edges
            cursor.execute(self.sql[69], (math.inf, graph))
            cursor.execute(self.sql[70], (vertex[0],))

        def loop_condition(graph: str, cursor: object) -> bool:
            """"""
            return 0 < cursor.execute(self.sql[71], (graph,)).fetchone()[0]

        def pop(graph: str, cursor: object) -> tuple:
            """"""
            next_vertex = cursor.execute(self.sql[72], (graph,)).fetchone()
            cursor.execute(self.sql[73], (graph, next_vertex[0])).fetchone()
            return next_vertex

        def adjacency(vertex: tuple, graph: str, cursor: object) -> list:
            """"""
            return cursor.execute(
                self.sql[74], (graph, vertex[0], graph, vertex[0], graph)
            ).fetchall()

        def push(
            adj_vertex: tuple, vertex: tuple, graph: str, cursor: object
        ) -> None:
            """"""
            weight = cursor.execute(
                self.sql[75],
                (graph, adj_vertex[0], vertex[0], adj_vertex[0], vertex[0]),
            ).fetchone()
            if weight is None:
                raise Exception("no weight?")
            if adj_vertex[3] == 0 and adj_vertex[2] > weight[0]:
                cursor.execute(
                    self.sql[76], (vertex[0], weight[0], adj_vertex[0])
                )

        start_vertex = self.cursor.execute(
            self.sql[77], (start_vertex_id,)
        ).fetchone()
        if start_vertex is None:
            raise Exception(f"edge '{start_vertex_id}' does not exist")

        self.bf_base(
            graph,
            start_vertex,
            enter=enter,
            loop_condition=loop_condition,
            pop=pop,
            adjacency=adjacency,
            push=push,
        )

    def single_source_shortest_path(
        self: object, graph: str, start_vertex_id: int
    ) -> bool:
        """"""

        def enter(vertex: tuple, graph: str, cursor: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM):
                raise Exception(
                    f"cannot alter vertices/edges/cycles of '{graph}'"
                )

            # initialize all edges
            cursor.execute(self.sql[78], (math.inf, graph))
            cursor.execute(self.sql[79], (vertex[0],))

        def loop_condition(graph: str, cursor: object) -> bool:
            """"""
            return 0 < cursor.execute(self.sql[80], (graph,)).fetchone()[0]

        def pop(graph: str, cursor: object) -> tuple:
            """"""
            next_vertex = cursor.execute(self.sql[81], (graph,)).fetchone()
            cursor.execute(self.sql[82], (graph, next_vertex[0])).fetchone()
            return next_vertex

        def adjacency(vertex: tuple, graph: str, cursor: object) -> list:
            """"""
            return cursor.execute(self.sql[83], (graph, vertex[0])).fetchall()

        def push(
            adj_vertex: tuple, vertex: tuple, graph: str, cursor: object
        ) -> None:
            """"""
            weight = cursor.execute(
                self.sql[84], (graph, vertex[0], adj_vertex[0])
            ).fetchone()
            if weight is None:
                raise Exception("no weight!")
            if adj_vertex[2] > vertex[2] + weight[0]:
                cursor.execute(
                    self.sql[85],
                    (vertex[0], vertex[2] + weight[0], adj_vertex[0]),
                )

        start_vertex = self.cursor.execute(
            self.sql[86], (start_vertex_id,)
        ).fetchone()
        if start_vertex is None:
            raise Exception(f"edge '{start_vertex_id}' does not exist")

        self.bf_base(
            graph,
            start_vertex,
            enter=enter,
            loop_condition=loop_condition,
            pop=pop,
            adjacency=adjacency,
            push=push,
        )

    def vbf_search(
        self: object, graph: str, start_vertex_id: int, **hooks: dict
    ) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
            raise Exception(
                f"cannot alter vertices/edges/cycles/cycle edges of '{graph}'"
            )

        # run enter hook
        hooks.get("enter", lambda x, y: None)(graph, self.cursor)

        # reset the vertices
        self.cursor.execute(
            """
            UPDATE vertex
            SET
                tree = NULL,
                color = 0,
                predecessor = NULL,
                bf_distance = ?,
                pushed = NULL
            WHERE graph_id = ?
            """,
            (math.inf, graph),
        )

        # initialize queue order paramter
        pushed = 0

        # fetch start vertex
        s = self.cursor.execute(
            """
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE graph_id = ? AND id = ?
                LIMIT 1
                """,
            (graph, start_vertex_id),
        ).fetchone()
        if s is None:
            raise Exception(
                f"vertex with id '{start_vertex_id}' not part of {graph}"
            )

        # push the edge to start
        hooks.get("before_enqueue", lambda x, y: None)(s, self.cursor)
        self.cursor.execute(
            """
            UPDATE
                vertex
            SET
                color = 1,
                predecessor = NULL,
                bf_distance = 0,
                pushed = ?
            WHERE
                graph_id = ? AND id = ?
            """,
            (pushed, graph, s[0]),
        )
        hooks.get("after_enqueue", lambda x, y: None)(
            s[:4] + (pushed,), self.cursor
        )

        # while there are vertices to handle
        while (
            self.cursor.execute(
                """
                SELECT COUNT(*)
                FROM vertex
                WHERE graph_id = ? AND pushed IS NOT NULL
                """,
                (graph,),
            ).fetchone()[0]
            > 0
        ):

            # fetch and dequeue the next vertex
            hooks.get("before_dequeue", lambda x: None)(self.cursor)
            u = self.cursor.execute(
                """
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE graph_id = ? AND pushed IS NOT NULL
                ORDER BY pushed ASC
                LIMIT 1
                """,
                (graph,),
            ).fetchone()
            self.cursor.execute(
                """
                UPDATE vertex
                SET color = 2, pushed = NULL
                WHERE id = ?
                """,
                (u[0],),
            )
            hooks.get("after_dequeue", lambda x, y: None)(u, self.cursor)

            # handle its descendents bf
            for v in self.cursor.execute(
                """
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE id IN (
                    SELECT child_vertex_id
                    FROM edge
                    WHERE parent_vertex_id = ?
                )
                UNION
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE id IN (
                    SELECT parent_vertex_id
                    FROM edge
                    WHERE child_vertex_id = ?
                )
                """,
                2 * (u[0],),
            ).fetchall():

                # adjacency hook
                hooks.get("handle_adjacency", lambda x, y, z: None)(
                    u, v, self.cursor
                )

                if v[2] == Color.white:
                    pushed += 1

                    # push descendent onto queue
                    hooks.get("before_enqueue", lambda x, y: None)(
                        v, self.cursor
                    )
                    self.cursor.execute(
                        """
                        UPDATE
                            vertex
                        SET
                            color = 1,
                            predecessor = ?,
                            bf_distance = ?,
                            pushed = ?
                        WHERE
                            graph_id = ? AND id = ?
                        """,
                        (u[0], u[4] + 1, pushed, graph, v[0]),
                    )
                    hooks.get("after_enqueue", lambda x, y: None)(
                        v[:4] + (pushed,), self.cursor
                    )

        # cleanup
        self.connection.commit()
        hooks.get("exit", lambda x, y: None)(graph, self.cursor)

    def flow_network_walk_vbf(
        self: object, graph: str, source_vertex_id: int, sink_vertex_id: int
    ) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
            raise Exception(
                f"cannot alter vertices/edges/cycles/cycle edges of '{graph}'"
            )

        # reset the vertices
        self.cursor.execute(
            """
            UPDATE vertex
            SET
                tree = NULL,
                color = 0,
                predecessor = NULL,
                bf_distance = ?,
                pushed = NULL
            WHERE graph_id = ?
            """,
            (math.inf, graph),
        )

        # initialize queue order paramter
        pushed = 0

        # fetch start vertex
        s = self.cursor.execute(
            """
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE graph_id = ? AND id = ?
                LIMIT 1
                """,
            (graph, source_vertex_id),
        ).fetchone()
        if s is None:
            raise Exception(
                f"vertex with id '{source_vertex_id}' not part of {graph}"
            )

        # push the vertex to start
        self.cursor.execute(
            """
            UPDATE
                vertex
            SET
                color = 1,
                predecessor = NULL,
                bf_distance = 0,
                pushed = ?
            WHERE
                graph_id = ? AND id = ?
            """,
            (pushed, graph, s[0]),
        )

        # while there are vertices to handle
        while (
            0
            < self.cursor.execute(
                """
            SELECT COUNT(*)
            FROM vertex
            WHERE graph_id = ? AND pushed IS NOT NULL
            """,
                (graph,),
            ).fetchone()[0]
        ):

            # fetch and dequeue the next vertex
            u = self.cursor.execute(
                """
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE graph_id = ? AND pushed IS NOT NULL
                ORDER BY pushed ASC
                LIMIT 1
                """,
                (graph,),
            ).fetchone()
            self.cursor.execute(
                """
                UPDATE vertex
                SET color = 2, pushed = NULL
                WHERE id = ?
                """,
                (u[0],),
            )

            # break early at sink
            if u[0] == sink_vertex_id:
                break

            # handle its descendents bf
            for v in self.cursor.execute(
                """
                SELECT id, tree, color, predecessor, bf_distance, pushed
                FROM vertex
                WHERE id IN (
                    SELECT e.child_vertex_id
                    FROM edge AS e
                    WHERE parent_vertex_id = ?
                    AND e.mf_capacity > e.mf_flow
                    AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
                )
                AND pushed IS NULL
                AND color = 0
                """,
                (u[0],),
            ).fetchall():

                pushed += 1

                self.cursor.execute(
                    """
                    UPDATE
                        vertex
                    SET
                        color = 1,
                        predecessor = ?,
                        bf_distance = ?,
                        pushed = ?
                    WHERE
                        graph_id = ? AND id = ?
                    """,
                    (u[0], u[4] + 1, pushed, graph, v[0]),
                )

        # cleanup
        self.connection.commit()

    def maximum_flow(
        self: object, graph: str, source_vertex_id: int, sink_vertex_id: int
    ) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM):
            raise Exception(f"cannot alter vertices/edges of '{graph}'")

        # set flows to zero
        self.cursor.execute(
            "UPDATE edge SET mf_flow = 0 WHERE graph_id = ?", (graph,)
        )

        def generate_edges():
            """"""
            chunk_cursor = self.connection.execute(
                """
                SELECT
                    id,
                    parent_vertex_id,
                    child_vertex_id,
                    mf_capacity,
                    metadata,
                    CASE
                        WHEN parent_vertex_id < child_vertex_id
                            THEN parent_vertex_id
                        ELSE child_vertex_id
                    END AS v1,
                    CASE
                        WHEN parent_vertex_id < child_vertex_id
                            THEN child_vertex_id
                        ELSE parent_vertex_id
                    END AS v2
                FROM
                    edge
                WHERE
                    graph_id = ?
                ORDER BY
                    v1, v2, parent_vertex_id, child_vertex_id
                """,
                (graph,),
            )
            while (chunk := chunk_cursor.fetchone()) is not None:
                yield chunk

        for _, edges in groupby(generate_edges(), lambda t: (t[5], t[6])):
            edges = list(edges)
            left_edges = [e for e in edges if e[5] < e[6]]
            right_edges = [e for e in edges if e[5] >= e[6]]

            if not left_edges and not right_edges:
                continue

            # split antiparallels
            for edge in right_edges:
                vertex_id = self.add_vertices(
                    graph, {"metadata": {"imaginary": True}}
                )[0]
                _ = self.add_edges(
                    graph,
                    {
                        "parent_vertex_id": edge[1],
                        "child_vertex_id": vertex_id,
                        "mf_capacity": 0,
                        "metadata": {"imaginary": True},
                    },
                    {
                        "parent_vertex_id": vertex_id,
                        "child_vertex_id": edge[1],
                        "mf_capacity": 0,
                        "metadata": {"imaginary": True},
                    },
                )
                self.alter_edge(
                    edge[0],
                    metadata=json.loads(edge[4] or "{}").update(
                        {"hiding": True}
                    ),
                )

        # main loop
        while True:

            # set predecessor for each vertex
            self.flow_network_walk_vbf(graph, source_vertex_id, sink_vertex_id)

            # evaluate path
            path = self.cursor.execute(
                """
                WITH RECURSIVE
                    path_vertices AS (
                        SELECT v.id, v.predecessor
                        FROM vertex AS v
                        WHERE id = ?
                        UNION ALL
                        SELECT v.id, v.predecessor
                        FROM vertex AS v
                        JOIN path_vertices AS pv
                            ON v.id = pv.predecessor
                        WHERE v.predecessor IS NOT NULL
                    ),
                    path_edges AS (
                        SELECT e.id, e.mf_capacity, e.mf_flow, e.metadata
                        FROM edge AS e
                        JOIN path_vertices AS pv
                            ON e.child_vertex_id = pv.id
                            AND e.parent_vertex_id = pv.predecessor
                    ),
                    path_complete_flag AS (
                        SELECT 1 FROM path_vertices WHERE predecessor = ?
                    )
                SELECT *
                FROM path_edges
                WHERE 1 IN (SELECT * FROM path_complete_flag)
                """,
                (sink_vertex_id, source_vertex_id),
            ).fetchall()

            # convergence (hopefully)
            if not path:
                break

            # path residual capacity
            path_residual_capcity = min(t[1] - t[2] for t in path)

            # update step
            for edge in path:
                if edge[1] - edge[2] == 0:
                    f = edge[2] - path_residual_capcity
                else:
                    f = edge[2] + path_residual_capcity
                self.cursor.execute(
                    "UPDATE edge SET mf_flow = ? WHERE id = ?", (f, edge[0])
                )
