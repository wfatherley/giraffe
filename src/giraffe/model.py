""""""

from sqlalchemy import MetaData, Table, Column
from sqlalchemy import Integer, String, ForeignKey, Numeric
from sqlalchemy import text

# giraffe model ddls
# ==================
metadata = MetaData()


graph = Table(
    "graph",
    metadata,
    Column("id", String(100), primary_key=True, autoincrement=False),
    Column("directed", Integer, nullable=False),
    Column("acyclic", Integer, nullable=True),
    Column("metadata", String(1000), nullable=True),
    Column("mode", Integer, nullable=True, default=0),
)


vertex = Table(
    "vertex",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column(
        "predecessor",
        Integer,
        ForeignKey("vertex.id"),
    ),
    Column("graph_id", String(100), ForeignKey("graph.id"), nullable=False),
    Column("aux_id", String(100), nullable=True),
    Column("bf_distance", Numeric, nullable=True),
    Column("pushed", Integer, nullable=True),
    Column("popped", Integer, nullable=True),
    Column("tree", Integer, nullable=True),
    Column("color", Integer, nullable=True, default=0),
    Column("metadata", String(1000), nullable=True),
    Column("sp_estimate", Numeric, nullable=True),
    Column("topological_id", Integer, nullable=True),
    Column("scc_index", Integer, nullable=True),
    Column("scc_lowlink", Integer, nullable=True),
    Column("scc_onstack", Integer, nullable=True),
    Column("mst_key", Numeric, nullable=True),
)


edge = Table(
    "edge",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=False),
    Column("transpose_id", Integer, ForeignKey("edge.id"), nullable=True),
    Column("predecessor", Integer, ForeignKey("edge.id"), nullable=True),
    Column(
        "parent_vertex_id", Integer, ForeignKey("vertex.id"), nullable=False
    ),
    Column(
        "child_vertex_id", Integer, ForeignKey("vertex.id"), nullable=False
    ),
    Column("graph_id", String(100), ForeignKey("graph.id"), nullable=False),
    Column("type", Integer, nullable=True),
    Column("tree", Integer, nullable=True),
    Column("color", Integer, nullable=True, default=0),
    Column("pushed", Integer, nullable=True),
    Column("popped", Integer, nullable=True),
    Column("component_graph_bridge", Integer, nullable=True),
    Column("metadata", String(1000), nullable=True),
    Column("weight", Numeric, nullable=True),
    Column("aux_id", String(100), nullable=True),
    Column("mf_capacity", Numeric, nullable=True),
    Column("mf_flow", Numeric, nullable=True, default=0),
)


cycle = Table(
    "cycle",
    metadata,
    Column("graph_id", String(100), ForeignKey("graph.id"), nullable=False),
    Column("cardinality", Integer, nullable=False),
    Column("inflow", Integer, nullable=True),
    Column("metadata", String(1000), nullable=True),
    Column("id", Integer, primary_key=True, autoincrement=False),
)


cycle_edge = Table(
    "cycle_edge",
    metadata,
    Column("cycle_id", Integer, ForeignKey("cycle.id"), nullable=False),
    Column("edge_id", Integer, ForeignKey("edge.id"), nullable=False),
)


# raw sql
# =======
graph_raw = """
    CREATE TABLE IF NOT EXISTS graph(

        id VARCHAR(100) NOT NULL,

        directed INT NOT NULL,
        acyclic INT,
        metadata VARCHAR(1000),
        mode int DEFAULT 0,

        PRIMARY KEY (id)
    )
"""


vertex_raw = """
    CREATE TABLE IF NOT EXISTS vertex(

        id INT PRIMARY KEY,
        predecessor INT REFERENCES vertex(id)
            ON DELETE SET NULL,

        graph_id VARCHAR(100) NOT NULL,

        aux_id VARCHAR(100),
        bf_distance NUMERIC,
        pushed INT,
        popped INT,
        tree INT,
        color INT DEFAULT 0,
        metadata VARCHAR(1000),
        sp_estimate NUMERIC,
        topological_id INT,
        scc_index INT,
        scc_lowlink INT,
        scc_onstack INT,
        mst_key NUMERIC,

        FOREIGN KEY (graph_id) REFERENCES graph(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
"""


edge_raw = """
    CREATE TABLE IF NOT EXISTS edge(

        id INT PRIMARY KEY,
        transpose_id INT REFERENCES edge(id)
            ON DELETE SET NULL,
        predecessor INT REFERENCES edge(id),

        parent_vertex_id INTEGER NOT NULL,
        child_vertex_id INTEGER NOT NULL,

        graph_id VARCHAR(100) NOT NULL,
        
        type INT,
        tree INT,
        color INT DEFAULT 0,
        pushed INT,
        popped INT,
        component_graph_bridge INT,
        metadata VARCHAR(1000),
        weight NUMERIC,
        aux_id VARCHAR(100),
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
    )
"""


cycle_raw = """
    CREATE TABLE IF NOT EXISTS cycle(
        graph_id VARCHAR(100) NOT NULL,
        cardinality INT NOT NULL,
        inflows INT,
        outflows INT,
        metadata VARCHAR(1000),

        id INT PRIMARY KEY,

        FOREIGN KEY (graph_id) REFERENCES graph(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
"""


cycle_edge_raw = """
    CREATE TABLE IF NOT EXISTS cycle_edge(
        cycle_id INT NOT NULL,
        edge_id INT NOT NULL,

        FOREIGN KEY (cycle_id) REFERENCES cycle(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE,
        FOREIGN KEY (edge_id) REFERENCES edge(id)
            ON DELETE CASCADE
            ON UPDATE CASCADE
    )
"""


dql_map_raw = {"check_mode": ["SELECT mode FROM graph WHERE id = :id"]}  # 0
dql_map_raw["model"] = [
    graph_raw,
    vertex_raw,
    edge_raw,
    cycle_raw,
    cycle_edge_raw,
]

dql_map_raw |= {
    "create_graph": [
        """
            INSERT INTO graph (id, directed, acyclic, metadata, mode)
            VALUES (
                :id,
                :directed,
                :acyclic,
                :metadata,
                :mode
            )
            """  # 0
    ]
}

dql_map_raw |= {
    "alter_graph": [
        """
        SELECT directed, acyclic, metadata, mode, id
        FROM graph
        WHERE id = :id
        """,
        """
        UPDATE graph
        SET
            directed = :directed,
            acyclic = :acyclic,
            metadata = :metadata,
            mode = :mode
        WHERE id = :id
        """,  # 1
    ]
}

dql_map_raw |= {"delete_graphs": ["DELETE FROM graph WHERE id = :id"]}  # 0

dql_map_raw |= {
    "add_vertices": [
        "SELECT COALESCE(MAX(id), -1) + 1 FROM vertex",  # 0
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
            :id,
            :predecessor,
            :graph_id,
            :aux_id,
            :bf_distance,
            :pushed,
            :popped,
            :tree,
            :color,
            :metadata,
            :sp_estimate,
            :topological_id,
            :scc_index,
            :scc_lowlink,
            :scc_onstack,
            :mst_key
        )
        RETURNING id
        """,  # 1
    ]
}

dql_map_raw |= {
    "alter_vertex": [
        "SELECT * FROM vertex WHERE id = :id",  # 0
        """
        UPDATE
            vertex
        SET
            predecessor = :predecessor,
            graph_id = :graph_id,
            aux_id = :aux_id,
            bf_distance = :bf_distance,
            pushed = :pushed,
            popped = :popped,
            tree = :tree,
            color = :color,
            metadata = :metadata,
            sp_estimate = :sp_estimate,
            topological_id = :topological_id,
            scc_index = :scc_index,
            scc_lowlink = :scc_lowlink,
            scc_onstack = :scc_onstack,
            mst_key = :mst_key
        WHERE
            id = :id
        """,  # 1
    ]
}

dql_map_raw |= {"delete_vertices": ["DELETE FROM vertex WHERE id = :id"]}  # 0

dql_map_raw |= {
    "add_edges": [
        "SELECT COALESCE(MAX(id), -1) + 1 FROM edge",  # 0
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
            :id,
            :transpose_id,
            :predecessor,
            :parent_vertex_id,
            :child_vertex_id,
            :graph_id,
            :type,
            :tree,
            :color,
            :pushed,
            :popped,
            :component_graph_bridge,
            :metadata,
            :weight,
            :aux_id,
            :mf_capacity,
            :mf_flow
        )
        RETURNING id
        """,  # 1
    ]
}

dql_map_raw |= {
    "alter_edge": [
        "SELECT * FROM edge WHERE id = :id",  # 0
        """
        UPDATE
            edge
        SET
            transpose_id = :transpose_id,
            predecessor = :predecessor,
            parent_vertex_id = :parent_vertex_id,
            child_vertex_id = :child_vertex_id,
            graph_id = :graph_id,
            type = :type,
            tree = :tree,
            color = :color,
            pushed = :pushed,
            popped = :popped,
            component_graph_bridge = :component_graph_bridge,
            metadata = :metadata,
            weight = :weight,
            aux_id = :aux_id,
            mf_capacity = :mf_capacity,
            mf_flow = :mf_flow

        WHERE
            id = :id
        """,  # 1
    ]
}

dql_map_raw |= {"delete_edges": ["DELETE FROM edge WHERE id = :id"]}  # 0

dql_map_raw |= {
    "transpose": [
        """
        INSERT INTO graph (id, acyclic, directed, metadata)
        VALUES (
            :id1,
            (SELECT acyclic FROM graph WHERE id = :id2),
            (SELECT directed FROM graph WHERE id = :id2), 
            :metadata
        )
        """,  # 0
        "SELECT id FROM vertex WHERE graph_id = :graph_id",  # 1
        """
        SELECT
            id, parent_vertex_id, child_vertex_id, component_graph_bridge
        FROM
            edge
        WHERE
            graph_id = :graph_id
        """,  # 2
        """
        UPDATE edge
        SET transpose_id = :transpose_id
        WHERE id = :id
        """,  # 3
    ]
}

dql_map_raw |= {
    "vdf_search": [
        """
        UPDATE vertex
        SET color = 0, pushed = NULL, popped = NULL
        WHERE graph_id = :graph_id
        RETURNING id
        """,  # 0
        """
        UPDATE vertex
        SET color = 1, pushed = :pushed, tree = :tree
        WHERE graph_id = :graph_id AND id = :id AND color = 0
        RETURNING id, tree, color, pushed, graph_id
        """,  # 1
        """
        SELECT v.id, v.tree, v.color, v.pushed, v.graph_id
        FROM vertex AS v
        INNER JOIN edge AS e
            ON e.child_vertex_id = v.id
        WHERE
            v.color = 0
            AND e.parent_vertex_id = :parent_vertex_id
            AND v.graph_id = :graph_id
        ORDER BY v.id
        """,  # 2
        """
        UPDATE vertex
        SET color = 1, pushed = :pushed, tree = :tree
        WHERE id = :id
        """,  # 3
        """
        UPDATE vertex
        SET color = 2, popped = :popped
        WHERE id = :id
        """,  # 4
        """
        SELECT id, tree, color, pushed, graph_id
        FROM vertex
        WHERE graph_id = :graph_id AND pushed = (
            SELECT MAX(pushed)
            FROM vertex
            WHERE tree = :tree AND color = 1 AND graph_id = :graph_id
        )
        """,  # 5
    ]
}

# dql_map_raw |= {
#     "vdf_search": [
#         """
#         UPDATE vertex
#         SET color = 0, pushed = NULL, popped = NULL
#         WHERE graph_id = :graph_id
#         RETURNING id
#         """,  # 0
#         """
#         WITH
#             this_vertex AS (
#                 UPDATE vertex
#                 SET color = 1, pushed = :pushed, tree = :tree
#                 WHERE graph_id = :graph_id AND id = :id AND color = 0
#                 RETURNING id, tree, color, pushed, graph_id
#             ),
#             branch_tips AS (
#                 SELECT v.id, v.tree, v.color, v.pushed, v.graph_id
#                 FROM vertex AS v
#                 INNER JOIN edge AS e
#                     ON e.child_vertex_id = v.id
#                 WHERE
#                     v.color = 0
#                     AND e.parent_vertex_id = (SELECT id FROM this_vertex)
#                     AND v.graph_id = :graph_id
#                 ORDER BY v.id
#             )
#         SELECT *, 0 FROM branch_tips
#         UNION
#         SELECT *, 1 FROM this_vertex
#         """,  # 1
#         """
#         WITH
#             do_update AS (
#                 UPDATE vertex
#                 SET color = 1, pushed = :pushed, tree = :tree
#                 WHERE id = :id
#                 RETURNING id
#             )
#         SELECT v.id, v.tree, v.color, v.pushed, v.graph_id
#         FROM vertex AS v
#         INNER JOIN edge AS e
#             ON e.child_vertex_id = v.id
#         WHERE
#             v.color = 0
#             AND e.parent_vertex_id = :id
#             AND v.graph_id = :graph_id
#         ORDER BY v.id
#         """,  # 2
#         """
#         UPDATE vertex
#         SET color = 2, popped = :popped
#         WHERE id = :id
#         """,  # 3
#         """
#         WITH
#             this_vertex AS (
#                 SELECT id, tree, color, pushed, graph_id
#                 FROM vertex
#                 WHERE graph_id = :graph_id AND pushed = (
#                     SELECT MAX(pushed)
#                     FROM vertex
#                     WHERE tree = :tree AND color = 1 AND graph_id = :graph_id
#                 )
#             ),
#             branch_tips AS (
#                 SELECT v.id, v.tree, v.color, v.pushed, v.graph_id
#                 FROM vertex AS v
#                 INNER JOIN edge AS e
#                     ON e.child_vertex_id = v.id
#                 WHERE
#                     v.color = 0
#                     AND e.parent_vertex_id = (SELECT id FROM this_vertex)
#                     AND v.graph_id = :graph_id
#                 ORDER BY v.id
#             )
#         SELECT *, 0 FROM branch_tips
#         UNION
#         SELECT *, 1 FROM branch_tips
#         """,  # 4
#     ]
# }

dql_map_raw |= {
    "edf_search": [
        """
        UPDATE edge
        SET tree = NULL, color = 0, pushed = NULL, popped = NULL
        WHERE graph_id = :graph_id
        RETURNING id
        """,  # 0
        """
        UPDATE
            edge
        SET
            color = 1, pushed = :pushed, tree = :tree
        WHERE
            graph_id = :graph_id AND id = :id AND color = 0
        RETURNING
            id,
            child_vertex_id,
            parent_vertex_id,
            tree,
            color,
            pushed,
            graph_id
        """,  # 1
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
            graph_id = :graph_id
            AND parent_vertex_id = :parent_vertex_id
        """,  # 2
        """
        UPDATE edge
        SET color = 1, pushed = :pushed, tree = :tree
        WHERE id = :id
        """,  # 3
        """
        UPDATE edge
        SET color = 2, popped = :popped
        WHERE id = :id
        """,  # 4
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
            graph_id = :graph_id
            AND pushed = (
                SELECT
                    MAX(pushed)
                FROM
                    edge
                WHERE
                    graph_id = :graph_id
                    AND tree = :tree
                    AND color = 1
                    AND child_vertex_id = :child_vertex_id
                LIMIT 1
            )
        """,  # 5
    ]
}

dql_map_raw |= {
    "find_cycles": [
        "DELETE FROM cycle WHERE graph_id = :graph_id",  # 0
        """
        SELECT cycle_id
        FROM cycle_edge
        WHERE edge_id = :edge_id
        LIMIT 1
        """,  # 1
        """
        SELECT id
        FROM edge
        WHERE
            pushed >= :pushed1
            AND pushed <= :pushed2
            AND color = 1
            AND tree = :tree
            AND graph_id = :graph_id
        """,  # 2
        """
        INSERT INTO cycle (id, graph_id, cardinality)
        VALUES (
            COALESCE((SELECT MAX(id) FROM cycle WHERE graph_id = :graph_id), -1) + 1,
            :graph_id,
            :cardinality
        )
        RETURNING id
        """,  # 3
        """
        INSERT INTO cycle_edge (cycle_id, edge_id)
        VALUES (:cycle_id, :edge_id)
        """,  # 4
        """
        SELECT cycle_id
        FROM cycle_edge
        WHERE edge_id = :edge_id
        LIMIT 1
        """,  # 5
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
            ce.cycle_id = :cycle_id AND e.pushed = e.popped - 1
        """,  # 6
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
            parent_vertex_id = :parent_vertex_id AND color = 1
        """,  # 7
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
            child_vertex_id = :child_vertex_id
            AND color = 1
            AND pushed = (SELECT MAX(pushed) FROM edge WHERE graph_id = :graph_id)
        """,  # 8
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
                    e.graph_id = :graph_id
                    AND e.tree = :tree
                    AND e.color = 2
                    AND e.pushed <= :pushed1
                    AND e.pushed >= :pushed2
                    AND ce.cycle_id = :cycle_id
                ORDER BY e.id
                LIMIT 1
            )
        """,  # 9
        """
        SELECT
            id
        FROM
            edge
        WHERE
            (
                pushed BETWEEN :pushed1 AND :pushed2
                OR pushed BETWEEN :pushed3 AND :pushed4
                OR pushed BETWEEN (
                    SELECT pushed
                    FROM edge
                    WHERE
                        parent_vertex_id = :parent_vertex_id
                        AND pushed = (
                            SELECT MAX(pushed)
                            FROM edge
                            WHERE parent_vertex_id = :parent_vertex_id
                        )
                ) AND :pushed5
            )
            AND tree = :tree
            AND graph_id = :graph_id
        """,  # 10
        "UPDATE graph SET acyclic = 0 WHERE id = :id",  # 11
    ]
}

dql_map_raw |= {
    "topological_sort": [
        "SELECT COUNT(*) FROM cycle WHERE graph_id = :graph_id",  # 0
        """
            SELECT id
            FROM vertex
            WHERE graph_id = :graph_id
            ORDER BY popped DESC
            """,  # 1
        """
            UPDATE vertex
            SET topological_id = :topological_id
            WHERE id = :id
            """,  # 2
    ]
}

dql_map_raw |= {
    "strongly_connected_components": [
        """
        UPDATE vertex
        SET scc_index = NULL, scc_lowlink = NULL, scc_onstack = 0
        WHERE graph_id = :graph_id
        """,  # 0
        """
        UPDATE
            vertex
        SET
            scc_index = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex WHERE graph_id = :graph_id), -1
            ),
            scc_lowlink = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex WHERE graph_id = :graph_id), -1
            ),
            scc_onstack = 1
        WHERE
            id = :id AND scc_index IS NULL
        """,  # 1
        """
        UPDATE
            vertex
        SET
            scc_index = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex WHERE graph_id = :graph_id), -1
            ),
            scc_lowlink = 1 + COALESCE(
                (SELECT MAX(scc_index) FROM vertex WHERE graph_id = :graph_id), -1
            ),
            scc_onstack = 1
        WHERE
            id = :id AND scc_index IS NULL
        RETURNING id, scc_index, scc_lowlink, scc_onstack
        """,  # 2
        """
        SELECT id, scc_index, scc_lowlink, scc_onstack
        FROM vertex
        WHERE id = :id
        """,  # 3
        """
        UPDATE vertex
        SET scc_lowlink = :scc_lowlink
        WHERE id = :id
        """,  # 4
        """
        UPDATE vertex
        SET scc_onstack = 0
        WHERE scc_lowlink = :scc_lowlink
        """,  # 5
        "UPDATE vertex SET scc_onstack = 0 WHERE id = :id",  # 6
    ]
}

dql_map_raw |= {
    "vbf_search": [
        """
        UPDATE vertex
        SET
            color = 0,
            tree = NULL,
            predecessor = NULL,
            bf_distance = :bf_distance,
            pushed = NULL
        WHERE graph_id = :graph_id
        """,  # 0
        "UPDATE vertex SET pushed = 1, color = 1 WHERE id = :id",  # 1
        """
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = :graph_id AND pushed > 0 AND color = 1
        """,  # 2
        """
        SELECT id, tree, predecessor, bf_distance, pushed
        FROM vertex
        WHERE graph_id = :graph_id AND color = 1
        ORDER BY pushed ASC
        LIMIT 1
        """,  # 3
        "UPDATE vertex SET color = 2 WHERE id = :id",  # 4
        """
        SELECT id, tree, predecessor, bf_distance, pushed
        FROM vertex
        WHERE color = 0 AND id IN (
            SELECT child_vertex_id
            FROM edge
            WHERE parent_vertex_id = :id
        )
        UNION
        SELECT id, tree, predecessor, bf_distance, pushed
        FROM vertex
        WHERE color = 0 AND id IN (
            SELECT parent_vertex_id
            FROM edge
            WHERE child_vertex_id = :id
        )
        """,  # 5
        # (
        #     SELECT vertex.id, vertex.predecessor, vertex.bf_distance, vertex.pushed
        #     FROM vertex
        #     WHERE
        #         vertex.color = :color_1
        #         AND vertex.id IN (
        #             SELECT edge.child_vertex_id
        #             FROM edge
        #             WHERE edge.parent_vertex_id = :b_id
        #         )
        #     ORDER BY vertex.pushed ASC
        # )
        # UNION
        # (
        #     SELECT vertex.id, vertex.predecessor, vertex.bf_distance, vertex.pushed
        #     FROM vertex
        #     WHERE
        #         vertex.color = :color_2
        #         AND vertex.id IN (
        #             SELECT edge.parent_vertex_id
        #             FROM edge
        #             WHERE edge.child_vertex_id = :b_id
        #         )
        #     ORDER BY vertex.pushed ASC
        # )
        """
        UPDATE
            vertex
        SET
            color = 1,
            predecessor = :predecessor,
            bf_distance = :bf_distance,
            pushed = (
                SELECT MAX(pushed) + 1
                FROM vertex
                WHERE graph_id = :graph_id
            )
        WHERE
            graph_id = :graph_id AND id = :id
        """,  # 6
        """
        SELECT id, tree, predecessor, bf_distance, NULL AS pushed
        FROM vertex
        WHERE id = :id
        """,  # 7
    ]
}

dql_map_raw |= {
    "ebf_search": [
        """
        UPDATE edge
        SET predecessor = NULL, pushed = NULL
        WHERE graph_id = :graph_id
        """,  # 0
        "UPDATE edge SET pushed = 1 WHERE id = :id",  # 1
        """
        SELECT COUNT(*)
        FROM edge
        WHERE graph_id = :graph_id AND pushed > 0
        """,  # 2
        """
        SELECT id, predecessor, pushed
        FROM edge
        WHERE graph_id = :graph_id AND pushed > 0
        ORDER BY pushed ASC
        LIMIT 1
        """,  # 3
        "UPDATE edge SET pushed = -1 * pushed WHERE id = :id",  # 4
        """
        WITH
            w AS (
                SELECT id, predecessor, pushed, child_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND parent_vertex_id = (
                    SELECT child_vertex_id FROM edge WHERE id = :id
                )
            ),
            y AS (
                SELECT id, predecessor, pushed, parent_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND child_vertex_id = (
                    SELECT child_vertex_id FROM edge WHERE id = :id
                )
            ),
            x AS (
                SELECT id, predecessor, pushed, child_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND parent_vertex_id = (
                    SELECT parent_vertex_id FROM edge WHERE id = :id
                )
            ),
            z AS (
                SELECT id, predecessor, pushed, parent_vertex_id AS v
                FROM edge
                WHERE pushed IS NULL AND child_vertex_id = (
                    SELECT parent_vertex_id FROM edge WHERE id = :id
                )
            ),
            a AS (
                SELECT *
                FROM (SELECT * FROM w UNION SELECT * FROM y)
                WHERE v NOT IN (
                    SELECT child_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> :id
                    UNION
                    SELECT parent_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> :id
                )
            ),
            b AS (
                SELECT *
                FROM (SELECT * FROM x UNION SELECT * FROM z)
                WHERE v NOT IN (
                    SELECT child_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> :id
                    UNION
                    SELECT parent_vertex_id
                    FROM edge
                    WHERE pushed IS NOT NULL AND id <> :id
                )
            )
            SELECT id, predecessor, pushed
            FROM (SELECT * FROM a UNION SELECT * FROM b)
            WHERE id NOT IN (
                SELECT a.id FROM a INNER JOIN b ON a.v = b.v
            )
        """,  # 5
        """
        UPDATE edge
        SET predecessor = :predecessor, pushed = (
            SELECT COALESCE(MAX(pushed), 1) + 1
            FROM edge
            WHERE graph_id = :graph_id AND pushed > 0
        )
        WHERE id = :id
        """,  # 6
        "UPDATE edge SET pushed = NULL WHERE graph_id = :graph_id",  # 7
        """
        SELECT id, predecessor, NULL AS pushed
        FROM edge
        WHERE id = :id
        """,  # 8
    ]
}

dql_map_raw |= {
    "minimum_spanning_tree": [
        """
        UPDATE vertex
        SET predecessor = NULL, color = 0, mst_key = CASE
            WHEN id = :id THEN 0
            ELSE :mst_key
        END
        WHERE graph_id = :graph_id
        """,  # 0
        """
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = :graph_id AND color = 0
        """,  # 1
        """
        UPDATE vertex
        SET color = 2
        WHERE id = (
            SELECT id
            FROM vertex
            WHERE graph_id = :graph_id AND color = 0
            ORDER BY mst_key ASC, id ASC
            LIMIT 1
        )
        RETURNING id, predecessor, mst_key, color
        """,  # 2
        """
        WITH
            x AS (
                SELECT parent_vertex_id AS id
                FROM edge
                WHERE
                    graph_id = :graph_id
                    AND child_vertex_id = :child_vertex_id
            ),
            y AS (
                SELECT child_vertex_id AS id
                FROM edge
                WHERE
                    graph_id = :graph_id
                    AND parent_vertex_id = :parent_vertex_id
            )
        SELECT id, predecessor, mst_key, color
        FROM vertex
        WHERE graph_id = :graph_id AND id IN (
            SELECT id FROM x
            UNION
            SELECT id FROM y
        )
        """,  # 3
        """
        SELECT weight
        FROM edge
        WHERE 
            (parent_vertex_id = :adj_id AND child_vertex_id = :id)
            OR (child_vertex_id = :adj_id AND parent_vertex_id = :id)
        ORDER BY weight ASC
        LIMIT 1
        """,  # 4
        """
        UPDATE vertex
        SET predecessor = :predecessor, mst_key = :mst_key
        WHERE id = :id
        """,  # 5
        """
        SELECT id, predecessor, mst_key, color
        FROM vertex
        WHERE id = :id
        """,  # 6
    ]
}

dql_map_raw |= {
    "single_source_shortest_path": [
        """
        UPDATE vertex
        SET sp_estimate = :sp_estimate, predecessor = NULL, color = 0
        WHERE graph_id = :graph_id
        """,  # 0
        """
        UPDATE vertex
        SET sp_estimate = 0, color = 0
        WHERE id = :id
        """,  # 1
        """
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = :graph_id AND color = 0
        """,  # 2
        """
        SELECT id, predecessor, sp_estimate, color
        FROM vertex
        WHERE graph_id = :graph_id AND color = 0
        ORDER BY sp_estimate ASC
        LIMIT 1
        """,  # 3
        """
        UPDATE vertex
        SET color = 2
        WHERE graph_id = :graph_id AND id = :id
        """,  # 4
        """
        SELECT
            v.id, v.predecessor, v.sp_estimate, v.color
        FROM
            edge AS e
        INNER JOIN
            vertex AS v
            ON v.id = e.child_vertex_id
        WHERE
            v.graph_id = :graph_id
            AND e.parent_vertex_id = :parent_vertex_id
        """,  # 5
        """
        SELECT weight
        FROM edge
        WHERE 
            graph_id = :graph_id
            AND (
                parent_vertex_id = :parent_vertex_id
                AND child_vertex_id = :child_vertex_id
            )
        """,  # 6
        """
        UPDATE vertex
        SET predecessor = :predecessor, sp_estimate = :sp_estimate
        WHERE id = :id
        """,  # 7
        """
        SELECT id, predecessor, sp_estimate, color
        FROM vertex
        WHERE id = :id
        """,  # 8
    ]
}

dql_map_raw |= {
    "flow_network_walk_vbf": [
        """
        UPDATE vertex
        SET
            tree = NULL,
            color = 0,
            predecessor = NULL,
            bf_distance = :bf_distance,
            pushed = NULL
        WHERE graph_id = :graph_id
        """,  # 0
        """
        SELECT id, tree, color, predecessor, bf_distance, pushed
        FROM vertex
        WHERE graph_id = :graph_id AND id = :id
        LIMIT 1
        """,  # 1
        """
        UPDATE
            vertex
        SET
            color = 1,
            predecessor = NULL,
            bf_distance = 0,
            pushed = :pushed
        WHERE
            graph_id = :graph_id AND id = :id
        """,  # 2
        """
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = :graph_id AND pushed IS NOT NULL
        """,  # 3
        """
        SELECT id, tree, color, predecessor, bf_distance, pushed
        FROM vertex
        WHERE graph_id = :graph_id AND pushed IS NOT NULL
        ORDER BY pushed ASC
        LIMIT 1
        """,  # 4
        """
        UPDATE vertex
        SET color = 2, pushed = NULL
        WHERE id = :id
        """,  # 5
        """
        SELECT id, tree, color, predecessor, bf_distance, pushed
        FROM vertex
        WHERE id IN (
            SELECT e.child_vertex_id
            FROM edge AS e
            WHERE parent_vertex_id = :parent_vertex_id
            AND e.mf_capacity > e.mf_flow
            AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
        )
        AND pushed IS NULL
        AND color = 0
        """,  # 6
        """
        UPDATE
            vertex
        SET
            color = 1,
            predecessor = :predecessor,
            bf_distance = :bf_distance,
            pushed = :pushed
        WHERE
            graph_id = :graph_id AND id = :id
        """,  # 7
    ]
}

dql_map_raw |= {
    "maximum_flow": [
        "UPDATE edge SET mf_flow = 0 WHERE graph_id = :graph_id",  # 0
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
            graph_id = :graph_id
        ORDER BY
            v1, v2, parent_vertex_id, child_vertex_id
        """,  # 1
        """
        WITH RECURSIVE
            path_vertices AS (
                SELECT v.id, v.predecessor
                FROM vertex AS v
                WHERE id = :id
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
                SELECT 1
                FROM path_vertices
                WHERE predecessor = :predecessor
            )
        SELECT *
        FROM path_edges
        WHERE 1 IN (SELECT * FROM path_complete_flag)
        """,  # 2
        "UPDATE edge SET mf_flow = :mf_flow WHERE id = :id",  # 3
    ]
}


for method, statements in dql_map_raw.items():
    for i, statement in enumerate(statements):
        if isinstance(statement, str):
            dql_map_raw[method][i] = text(statement)
