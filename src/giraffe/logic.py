"""A database-oriented library for handling graphs.

Giraffe uses SQLAlchemy and a simple relational model to store,
manipulate, and analyze graphs in a relational database. The model
looks like this:

.. raw:: html

   <object data="mermaid/model.svg" type="image/svg+xml"></object>


"""

import json
import math

from collections import OrderedDict
from enum import IntEnum
from itertools import groupby

import sqlalchemy

from .model import dql_map_raw


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

    WHITE = 0
    GRAY = 1
    BLACK = 2


class _Giraffe:
    """Composition of one DBAPI connection and graph methods.

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

    sql: dict | None = None
    metadata: sqlalchemy.MetaData = None

    def __init__(
        self, engine: object, infinity: int = 2**32 - 1, **execution_options
    ) -> None:
        """
        :param connection: a PEP-249 compliant database connection

        :return None:
        """

        self.inf = infinity

        # bind connection
        self.connection = engine.connect().execution_options(
            **execution_options
        )

    def close(self: object) -> None:
        """Close the cursor then close the connection.

        :return None:
        """
        self.connection.close()

    def load_schema(self: object) -> None:
        """Execute the model and commit.

        :return None:"""
        self.metadata.create_all(self.connection)

    def check_mode(self: object, graph: str, *flags: list) -> bool:
        """Determine if any of the given "mutability mode" flags are
        set for the graph.

        :param graph: name of the graph to check
        :param flags: zero or more mode flags to check

        :return bool:
        """

        # fetch the mode of graph
        mode = self.connection.execute(
            self.sql["check_mode"][0], {"id": graph}
        ).fetchone()

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
        """Create a graph. Optional keyword arguments are serialized as a JSON
        object and stored as metadata for the graph.

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
        self.connection.execute(
            self.sql["create_graph"][0],
            {
                "id": name,
                "directed": directed,
                "acyclic": acyclic,
                "metadata": metadata,
                "mode": mode,
            },
        )

    def alter_graph(self: object, name: str, **attributes) -> None:
        """Update attributes of a graph with any keyword arguments. Raise
        ``Exception`` if any keyword is not a valid graph attribute or if no
        attributes are provided.

        :param name: name of the graph to update
        :param attributes: graph attributes to update with

        :return None:"""

        # raise if called with nothing to alter with
        if not attributes:
            raise Exception(f"no attributes provided to update '{name}'")

        # fetch current record and update it
        record = (
            self.connection.execute(self.sql["alter_graph"][0], {"id": name})
            .fetchone()
            ._asdict()
        )
        for attribute in attributes:
            if attribute in record:
                record[attribute] = attributes[attribute]
            else:
                raise Exception(f"attribute '{attribute}' not part of graph")

        # dump metadata if it's a dictionary
        if record.get("metadata") is not None:
            record["metadata"] = json.dumps(record["metadata"])

        # update
        self.connection.execute(
            self.sql["alter_graph"][1], {"" + k: record[k] for k in record}
        )

    def delete_graphs(self: object, *names: list[str]) -> None:
        """Delete graphs with the given names.

        :param names: names of the graphs to delete

        :return None:
        """
        self.connection.execute(
            self.sql["delete_graphs"][0], [{"id": n} for n in names]
        )

    def add_vertices(
        self: object, graph: str, *vertices: list[dict]
    ) -> list[int]:
        """Add vertices to graph ``graph``. If a vertex has a "metadata" key,
        assume the corresponding value is a dictionary and dump it as a JSON
        object using ``json.dumps``. Raise ``Exception`` if a vertex has keys
        that are not valid vertex attributes. Return a list of ids for the
        created vertices.

        :param graph: name of the graph to add vertices to
        :param vertices: one or more dictionaries containing vertex attributes

        :return list[int]:
        """

        next_id = self.connection.execute(
            self.sql["add_vertices"][0]
        ).scalar_one()

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
                self.connection.execute(
                    self.sql["add_vertices"][1],
                    {"" + k: vertex_template[k] for k in vertex_template},
                ).scalar_one()
            )

        # return the created vertices
        return new_ids

    def alter_vertex(self: object, vertex_id: str, **attributes) -> None:
        """Update attributes of a vertex with any keyword arguments. Raise
        ``Exception`` if any keyword is not a valid vertex attribute or if no
        attributes are provided. Assume a "metadata" keyword argument is a
        dictionary and dump it as a JSON object using ``json.dumps``.

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
        record = (
            self.connection.execute(
                self.sql["alter_vertex"][0], {"id": vertex_id}
            )
            .fetchone()
            ._asdict()
        )
        for attribute_name, attribute in attributes.items():
            if attribute_name in record:
                record[attribute_name] = attribute
            else:
                raise Exception(
                    f"attribute '{attribute_name}' not part of vertex"
                )

        # dump metadata if it's not a string
        if record["metadata"] is not None:
            record["metadata"] = json.dumps(record["metadata"])

        # update
        self.connection.execute(
            self.sql["alter_vertex"][1], {"" + k: record[k] for k in record}
        )

    def delete_vertices(self: object, *ids: list[str]) -> None:
        """Delete vertices with the given ids.

        :param ids: ids of the vertices to delete

        :return None:"""
        self.connection.execute(
            self.sql["delete_vertices"][0], [{"id": i} for i in ids]
        )

    def add_edges(self: object, graph: str, *edges: list[dict]) -> list[int]:
        """Add edges to graph ``graph``. If an edge has a "metadata" key,
        assume the corresponding value is a dictionary and dump it as a JSON
        object using ``json.dumps``. Raise ``Exception`` if an edge has keys
        that are not valid edge attributes. Return a list of ids for the
        created edges.

        :param graph: name of the graph to add edges to
        :param edges: one or more dictionaries containing edge attributes

        :return list[int]:"""
        next_id = self.connection.execute(
            self.sql["add_edges"][0]
        ).scalar_one()

        # format edge dicts
        new_ids = []
        for i, edge in enumerate(edges):

            # fetch a template edge dictionary
            edge_template = edge_odict_factory()

            # raise if bad vertex attrs
            if set(edge) - set(edge_template):
                raise Exception("bad edge attributes")

            edge_template["graph_id"] = graph

            # dump metadata
            if edges[i].get("metadata") is not None:
                edge_template["metadata"] = json.dumps(
                    edges[i].pop("metadata")
                )

            # fill in any missing columns
            for attr in edge:
                edge_template[attr] = edges[i][attr]

            if edge_template["id"] is None:
                edge_template["id"] = next_id
                next_id += 1

            # add the edge
            new_ids.append(
                self.connection.execute(
                    self.sql["add_edges"][1],
                    {"" + k: edge_template[k] for k in edge_template},
                ).scalar_one()
            )

        # return the created vertices
        return new_ids

    def alter_edge(self: object, edge_id: str, **attributes) -> None:
        """Update attributes of an edge with any keyword arguments. Raise
        ``Exception`` if any keyword is not a valid edge attribute or if no
        attributes are provided. Assume a "metadata" keyword argument is a
        dictionary and dump it as a JSON object using ``json.dumps``.

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
        record = (
            self.connection.execute(self.sql["alter_edge"][0], {"id": edge_id})
            .fetchone()
            ._asdict()
        )
        for attribute_name, attribute in attributes.items():
            if attribute_name in record:
                record[attribute_name] = attribute
            else:
                raise Exception(
                    f"attribute '{attribute_name}' not part of edge"
                )

        # dump metadata if it's not a string
        if record["metadata"] is not None:
            record["metadata"] = json.dumps(record["metadata"])

        # udpate
        self.connection.execute(
            self.sql["alter_edge"][1], {"" + k: record[k] for k in record}
        )

    def delete_edges(self: object, *ids: list[str]) -> None:
        """Delete edges with the given ids.

        :param ids: ids of the edges to delete

        :return None:"""
        self.connection.execute(
            self.sql["delete_edges"][0], [{"id": i} for i in ids]
        )

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
        """Reverse the direction of all edges in a directed graph. Raise
        ``Exception`` if the graph's edges are immutable.

        :param graph: name of the graph to transpose
        :param transposed_name: new name (default ``graph + "_transpose"``)
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
        self.connection.execute(
            self.sql["transpose"][0],
            {
                "id1": transposed_name,
                "id2": graph,
                "metadata": json.dumps({"graph": graph}),
            },
        )

        # clone vertices with chunked pattern
        result = self.connection.execute(
            self.sql["transpose"][1], {"graph_id": graph}
        )
        while chunk := result.fetchmany(size=chunk_size):

            # store G's vertex id in metadata
            _ = self.add_vertices(
                transposed_name,
                *[
                    {"metadata": {"graph": graph, "vertex": v[0]}}
                    for v in chunk
                ],
            )

        # clone edges with chunked pattern
        result = self.connection.execute(
            self.sql["transpose"][2], {"graph_id": graph}
        )
        while chunk := result.fetchmany(size=chunk_size):

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

            self.connection.execute(
                self.sql["transpose"][3],
                [
                    {"transpose_id": t, "id": e[0]}
                    for t, e in zip(transpose_edge_ids, chunk)
                ],
            )

        # clean up
        return transposed_name

    def vdf_search(self: object, graph: str, **hooks: dict) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
            raise Exception(
                f"cannot alter vertices/edges/cycles/cycle edges of '{graph}'"
            )

        # run enter hook
        hooks.get("enter", lambda y, z: None)(graph, self.connection)

        # initialization
        current_time = 0
        self.connection.execute(self.sql["vdf_search"][0], {"graph_id": graph})
        # TODO: update above and select below can be mergred?
        # vertex ids can be used as a tree ids
        tree_result = self.connection.execute(
            self.sql["vdf_search"][1], {"graph_id": graph}
        ).scalars()
        while (tree := next(tree_result, None)) is not None:

            # push this tree's first vertex
            hooks.get("before_push", lambda x, y, z: None)(
                None, None, self.connection
            )
            vertex = self.connection.execute(
                self.sql["vdf_search"][2],
                {
                    "pushed": current_time,
                    "tree": tree,
                    "graph_id": graph,
                    "id": tree,
                },
            ).fetchone()

            # vertex with id 'tree' was not white
            if vertex is None:
                continue
            # TODO: merge update-returing above and select below in cte
            # fetch vertices growing off current vertex
            branch_tips = self.connection.execute(
                self.sql["vdf_search"][3],
                {"parent_vertex_id": vertex[0], "graph_id": graph},
            ).fetchall()

            # compute stack height to use below as break condition
            tree_size = self.connection.execute(
                self.sql["vdf_search"][4],
                {"graph_id": graph, "tree": tree},
            ).fetchone()[0]
            # TODO: manage tree size w/o db?

            # new tree created, trigger hook
            hooks.get("new_tree", lambda w, x, y, z: None)(
                tree_size, vertex, branch_tips, self.connection
            )

            # vertex pushed, trigger hook and increment current time
            hooks.get("after_push", lambda x, y, z: None)(
                vertex, branch_tips, self.connection
            )
            current_time += 1

            # while the stack is not empty
            while tree_size > 0:

                # handle any possible cycles
                hooks.get("iteration_begin", lambda v, w, x, y, z: None)(
                    tree, current_time, vertex, branch_tips, self.connection
                )

                # found an vertex to push
                if Color.WHITE in (v[2] for v in branch_tips):

                    # depth first doesn't care which vertex to pick
                    vertex = next(
                        filter(lambda e: e[2] == Color.WHITE, branch_tips)
                    )

                    # push this vertex
                    hooks.get("before_push", lambda x, y, z: None)(
                        vertex, branch_tips, self.connection
                    )
                    self.connection.execute(
                        self.sql["vdf_search"][5],
                        {
                            "pushed": current_time,
                            "tree": tree,
                            "id": vertex[0],
                        },
                    )

                    # fetch vertices growing off current vertex
                    branch_tips = self.connection.execute(
                        self.sql["vdf_search"][3],
                        {"parent_vertex_id": vertex[0], "graph_id": graph},
                    ).fetchall()
                    hooks.get("after_push", lambda x, y, z: None)(
                        vertex, branch_tips, self.connection
                    )
                    current_time += 1
                    tree_size += 1

                    # don't enter pop loop
                    continue

                # no more vertices to push, do a pop loop
                while Color.WHITE not in (v[2] for v in branch_tips):

                    # pop the vertex
                    hooks.get("before_pop", lambda x, y, z: None)(
                        vertex, branch_tips, self.connection
                    )
                    self.connection.execute(
                        self.sql["vdf_search"][6],
                        {"popped": current_time, "id": vertex[0]},
                    )
                    current_time += 1
                    tree_size -= 1

                    # leave pop loop if stack is empty
                    if tree_size == 0:
                        break

                    # set vertex to new stack top
                    vertex = self.connection.execute(
                        self.sql["vdf_search"][7],
                        {"graph_id": graph, "tree": tree},
                    ).fetchone()

                    # ask stack top for its branch tips
                    branch_tips = self.connection.execute(
                        self.sql["vdf_search"][3],
                        {"parent_vertex_id": vertex[0], "graph_id": graph},
                    ).fetchall()
                    hooks.get("after_pop", lambda x, y, z: None)(
                        vertex, branch_tips, self.connection
                    )

                # run return hook
                if hooks.get("return_early", lambda y, z: False)(
                    graph, self.connection
                ):
                    return

        # commit changes and exit
        hooks.get("exit", lambda y, z: None)(graph, self.connection)

    def edf_search(self: object, graph: str, **hooks: dict) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
            raise Exception(
                f"cannot alter vertices/edges/cycles/cycle edges of '{graph}'"
            )

        # run enter hook
        hooks.get("enter", lambda y, z: None)(graph, self.connection)

        # initialization
        current_time = 0
        self.connection.execute(self.sql["edf_search"][0], {"graph_id": graph})

        # edge ids can be used as a tree ids
        tree_result = self.connection.execute(
            self.sql["edf_search"][1], {"graph_id": graph}
        ).scalars()
        while (tree := next(tree_result, None)) is not None:

            # push this tree's first edge
            hooks.get("before_push", lambda x, y, z: None)(
                None, None, self.connection
            )
            edge = self.connection.execute(
                self.sql["edf_search"][2],
                {
                    "pushed": current_time,
                    "tree": tree,
                    "graph_id": graph,
                    "id": tree,
                },
            ).fetchone()

            # edge with id 'tree' was not white
            if edge is None:
                continue

            # fetch edges growing off current edge
            branch_tips = self.connection.execute(
                self.sql["edf_search"][3],
                {"graph_id": graph, "parent_vertex_id": edge[1]},
            ).fetchall()

            # compute stack height to use below as break condition
            tree_size = self.connection.execute(
                self.sql["edf_search"][4],
                {"graph_id": graph, "tree": tree},
            ).fetchone()[0]

            # new tree created, trigger hook
            hooks.get("new_tree", lambda w, x, y, z: None)(
                tree_size, edge, branch_tips, self.connection
            )

            # edge pushed, trigger hook and increment current time
            hooks.get("after_push", lambda x, y, z: None)(
                edge, branch_tips, self.connection
            )
            current_time += 1

            # while the stack is not empty
            while tree_size > 0:

                # handle any possible cycles
                hooks.get("iteration_begin", lambda v, w, x, y, z: None)(
                    tree, current_time, edge, branch_tips, self.connection
                )

                # found an edge to push
                if Color.WHITE in (e[4] for e in branch_tips):

                    # depth first doesn't care which edge to pick
                    edge = next(
                        filter(lambda e: e[4] == Color.WHITE, branch_tips)
                    )

                    # push this edge
                    hooks.get("before_push", lambda x, y, z: None)(
                        edge, branch_tips, self.connection
                    )
                    self.connection.execute(
                        self.sql["edf_search"][5],
                        {
                            "pushed": current_time,
                            "tree": tree,
                            "id": edge[0],
                        },
                    )

                    # fetch edges growing off current edge
                    branch_tips = self.connection.execute(
                        self.sql["edf_search"][3],
                        {"graph_id": graph, "parent_vertex_id": edge[1]},
                    ).fetchall()
                    hooks.get("after_push", lambda x, y, z: None)(
                        edge, branch_tips, self.connection
                    )
                    current_time += 1
                    tree_size += 1

                    # don't enter pop loop
                    continue

                # no more edges to push, do a pop loop
                while Color.WHITE not in (t[4] for t in branch_tips):

                    # pop the edge
                    hooks.get("before_pop", lambda x, y, z: None)(
                        edge, branch_tips, self.connection
                    )
                    self.connection.execute(
                        self.sql["edf_search"][6],
                        {"popped": current_time, "id": edge[0]},
                    )
                    current_time += 1
                    tree_size -= 1

                    # leave pop loop if stack is empty
                    if tree_size == 0:
                        break

                    # set edge to new stack top
                    edge = self.connection.execute(
                        self.sql["edf_search"][7],
                        {
                            "graph_id": graph,
                            "tree": tree,
                            "child_vertex_id": edge[2],
                        },
                    ).fetchone()

                    # ask stack top for its branch tips
                    branch_tips = self.connection.execute(
                        self.sql["edf_search"][3],
                        {"graph_id": graph, "parent_vertex_id": edge[1]},
                    ).fetchall()
                    hooks.get("after_pop", lambda x, y, z: None)(
                        edge, branch_tips, self.connection
                    )

                # run return hook
                if hooks.get("return_early", lambda y, z: False)(
                    graph, self.connection
                ):
                    return

        # commit changes and exit
        hooks.get("exit", lambda y, z: None)(graph, self.connection)

    def find_cycles(self: object, graph: str) -> None:
        """"""

        if self.check_mode(graph, CYIM, CEIM):
            raise Exception(f"cannot alter cycles of '{graph}'")

        # delete existing cycles
        self.connection.execute(
            self.sql["find_cycles"][0], {"graph_id": graph}
        )

        def cycles_handler(
            tree: int,
            current_time: int,
            edge: tuple,
            branch_tips: list[tuple],
            connection: object,
        ) -> None:
            """"""

            # flag to know if must update graph.acyclic
            update_graph_table = False

            # current graph
            graph_id = edge[6]

            # edge's cycle if any
            edge_cycle_id = connection.execute(
                self.sql["find_cycles"][1],
                {"edge_id": edge[0]},
            ).fetchone()
            if edge_cycle_id is not None:
                edge_cycle_id = edge_cycle_id[0]

            # for each gray-bump cycle found
            for bt in (e for e in branch_tips if e[4] == Color.GRAY):

                # fetch the edge ids of the cycle
                cycle_edge_ids = connection.execute(
                    self.sql["find_cycles"][2],
                    {
                        "pushed1": bt[5],
                        "pushed2": current_time,
                        "tree": tree,
                        "graph_id": graph_id,
                    },
                ).fetchall()

                # create a cycle record and return its id
                cycle_id = connection.execute(
                    self.sql["find_cycles"][3],
                    {
                        "graph_id": graph_id,
                        "cardinality": len(cycle_edge_ids),
                    },
                ).scalar_one()

                # and use cycle_id and cycle_edge_ids to create cycle_edge
                # records
                connection.execute(
                    self.sql["find_cycles"][4],
                    [
                        {"cycle_id": cycle_id, "edge_id": edge_id[0]}
                        for edge_id in cycle_edge_ids
                    ],
                )

                # and set update graph falg to true
                update_graph_table = True

            # for each edge, D, that a new cycle was closed on
            black_tips = tuple(
                e for e in branch_tips if e[4] == Color.BLACK and e[3] == tree
            )
            for D in black_tips:

                # fetch piggyback cycle id
                _ = connection.execute(
                    self.sql["find_cycles"][5],
                    {"edge_id": D[0]},
                ).fetchone()

                # continue if piggyback cycle doesnt exist
                if _ is None:
                    continue

                # set piggyback cycle id
                piggyback_cycle_id = _[0]

                # continue if piggyback cycle is edge's cycle
                if piggyback_cycle_id == edge_cycle_id:
                    continue

                # fetch E, edge that closed piggyback cycle
                E = connection.execute(
                    self.sql["find_cycles"][6],
                    {"cycle_id": piggyback_cycle_id},
                ).fetchone()

                if E is None:
                    continue

                # fetch A, edge that E closed piggyback cycle on
                A = connection.execute(
                    self.sql["find_cycles"][7],
                    {"parent_vertex_id": E[1]},
                ).fetchone()

                if A is None:
                    continue

                # fetch C, edge that closed new cycle onto D
                C = connection.execute(
                    self.sql["find_cycles"][8],
                    {"child_vertex_id": D[2], "graph_id": graph_id},
                ).fetchone()

                if C is None:
                    continue

                # fetch B, from which new cycle forks from piggyback
                B = connection.execute(
                    self.sql["find_cycles"][9],
                    {
                        "graph_id": graph_id,
                        "tree": tree,
                        "pushed1": C[5],
                        "pushed2": A[5],
                        "cycle_id": piggyback_cycle_id,
                    },
                ).fetchone()

                if B is None:
                    continue

                # fetch the new cycle edges
                cycle_edges = connection.execute(
                    self.sql["find_cycles"][10],
                    {
                        "pushed1": A[5],
                        "pushed2": B[5],
                        "pushed3": D[5],
                        "pushed4": E[5],
                        "parent_vertex_id": B[1],
                        "pushed5": C[5],
                        "tree": tree,
                        "graph_id": graph_id,
                    },
                ).fetchall()

                # create new cycle record
                cycle_id = connection.execute(
                    self.sql["find_cycles"][3],
                    {
                        "graph_id": graph_id,
                        "cardinality": len(cycle_edges),
                    },
                ).fetchone()[0]

                # insert new cycle edges
                connection.execute(
                    self.sql["find_cycles"][4],
                    [
                        {"cycle_id": cycle_id, "edge_id": e[0]}
                        for e in cycle_edges
                    ],
                )

                # set update graph flag to true
                update_graph_table = True

            # update the graph's acyclic column
            if update_graph_table:
                connection.execute(
                    self.sql["find_cycles"][11],
                    {"id": graph_id},
                )

        # run the search
        self.edf_search(graph, iteration_begin=cycles_handler)

    def topological_sort(self: object, graph: str) -> None:
        """"""

        # raise if graph is marked acyclic
        if (
            self.connection.execute(
                self.sql["topological_sort"][0], {"graph_id": graph}
            ).fetchone()[0]
            > 0
        ):
            raise Exception(f"graph '{graph}' is not acyclic")

        # run dfs
        self.vdf_search(graph)

        # add topoligcal sort ids
        topological_id = 0
        for vertex in self.connection.execute(
            self.sql["topological_sort"][1],
            {"graph_id": graph},
        ).fetchall():
            self.connection.execute(
                self.sql["topological_sort"][2],
                {"topological_id": topological_id, "id": vertex[0]},
            )
            topological_id += 1

    def strongly_connected_components(self: object, graph: str) -> None:
        """"""

        # initialize vertices
        self.connection.execute(
            self.sql["strongly_connected_components"][0], {"graph_id": graph}
        )

        # new tree hook
        def new_tree(
            tree_size: int,
            edge: tuple,
            branch_tips: list[tuple],
            connection: object,
        ) -> None:
            """"""

            # initialize scc attributes of the starting vertex
            connection.execute(
                self.sql["strongly_connected_components"][1],
                {"id": edge[2], "graph_id": graph},
            )

        # after push hook
        def after_push(
            edge: tuple, branch_tips: list[tuple], connection: object
        ) -> None:
            """"""

            # fetch child vertex
            child = connection.execute(
                self.sql["strongly_connected_components"][2],
                {"id": edge[1], "graph_id": graph},
            ).fetchone()
            if child is None:
                child = connection.execute(
                    self.sql["strongly_connected_components"][3],
                    {"id": edge[1]},
                ).fetchone()

            # don't interact with other components
            if child[1] != child[2]:
                return

            # fetch parent
            parent = connection.execute(
                self.sql["strongly_connected_components"][3], {"id": edge[2]}
            ).fetchone()

            # parent inherets component's smallest lowlink or its own
            if Color.WHITE not in (t[4] for t in branch_tips):
                connection.execute(
                    self.sql["strongly_connected_components"][4],
                    {
                        "scc_lowlink": min(parent[2], child[1]),
                        "id": parent[0],
                    },
                )

        # after pop hook
        def before_pop(
            edge: tuple, branch_tips: list[tuple], connection: object
        ) -> None:
            """"""

            # fetch scc attributes of parent and child vertex
            parent = connection.execute(
                self.sql["strongly_connected_components"][3], {"id": edge[2]}
            ).fetchone()
            child = connection.execute(
                self.sql["strongly_connected_components"][3], {"id": edge[1]}
            ).fetchone()

            # bumped into a component vertex, adjust its lowlink
            if child[3] == 1:
                connection.execute(
                    self.sql["strongly_connected_components"][4],
                    {
                        "scc_lowlink": min(parent[2], child[2]),
                        "id": parent[0],
                    },
                )

            # pop parent vertex off scc stack
            if child[2] == parent[1]:
                connection.execute(
                    self.sql["strongly_connected_components"][5],
                    {"scc_lowlink": parent[1]},
                )
            if not branch_tips:
                connection.execute(
                    self.sql["strongly_connected_components"][6],
                    {"id": child[0]},
                )

        self.edf_search(
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
        enter(start_obj, graph, self.connection)
        while loop_condition(graph, self.connection):
            obj = pop(graph, self.connection)
            for adjacent_obj in adjacency(obj, graph, self.connection):
                push(adjacent_obj, obj, graph, self.connection)
            iteration_complete(adjacent_obj, obj, graph, self.connection)
        tixe(graph, self.connection)

    def vbf_search(self: object, graph: str, start_vertex_id: int) -> None:
        """"""

        def enter(vertex: tuple, graph: str, connection: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM):
                raise Exception(f"cannot alter vertices/edges of '{graph}'")

            # initialize all edges
            connection.execute(
                self.sql["vbf_search"][0],
                {"bf_distance": 0, "graph_id": graph},
            )
            connection.execute(self.sql["vbf_search"][1], {"id": vertex[0]})

        def loop_condition(graph: str, connection: object) -> bool:
            """"""
            return (
                0
                < connection.execute(
                    self.sql["vbf_search"][2], {"graph_id": graph}
                ).fetchone()[0]
            )

        def pop(graph: str, connection: object) -> tuple:
            """"""
            next_edge = connection.execute(
                self.sql["vbf_search"][3], {"graph_id": graph}
            ).fetchone()
            connection.execute(self.sql["vbf_search"][4], {"id": next_edge[0]})
            return next_edge

        def adjacency(vertex: tuple, graph: str, connection: object) -> list:
            """"""
            return connection.execute(
                self.sql["vbf_search"][5], {"id": vertex[0]}
            ).fetchall()

        def push(
            adj_vertex: tuple, vertex: tuple, graph: str, connection: object
        ) -> None:
            """"""
            connection.execute(
                self.sql["vbf_search"][6],
                {
                    "predecessor": vertex[0],
                    "bf_distance": vertex[3] + 1,
                    "graph_id": graph,
                    "id": adj_vertex[0],
                },
            )

        # fetch start vertex data
        start_vertex = self.connection.execute(
            self.sql["vbf_search"][7], {"id": start_vertex_id}
        ).fetchone()
        if start_vertex is None:
            raise Exception(f"vertex '{start_vertex_id}' does not exist")

        self.bf_base(
            graph,
            start_vertex,
            enter=enter,
            loop_condition=loop_condition,
            pop=pop,
            adjacency=adjacency,
            push=push,
        )

    def ebf_search(self: object, graph: str, start_edge_id: int) -> None:
        """"""

        def enter(edge: tuple, graph: str, connection: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM):
                raise Exception(f"cannot alter vertices/edges of '{graph}'")

            # initialize all edges
            connection.execute(self.sql["ebf_search"][0], {"graph_id": graph})
            connection.execute(self.sql["ebf_search"][1], {"id": edge[0]})

        def loop_condition(graph: str, connection: object) -> bool:
            """"""
            return (
                0
                < connection.execute(
                    self.sql["ebf_search"][2], {"graph_id": graph}
                ).fetchone()[0]
            )

        def pop(graph: str, connection: object) -> tuple:
            """"""
            next_edge = connection.execute(
                self.sql["ebf_search"][3], {"graph_id": graph}
            ).fetchone()
            connection.execute(self.sql["ebf_search"][4], {"id": next_edge[0]})
            return next_edge

        def adjacency(edge: tuple, graph: str, connection: object) -> list:
            """"""
            return connection.execute(
                self.sql["ebf_search"][5], {"id": edge[0]}
            ).fetchall()

        def push(
            adj_edge: tuple, edge: tuple, graph: str, connection: object
        ) -> None:
            """"""
            connection.execute(
                self.sql["ebf_search"][6],
                {
                    "predecessor": edge[0],
                    "graph_id": graph,
                    "id": adj_edge[0],
                },
            )

        def tixe(graph: str, connection: object) -> None:
            """"""
            connection.execute(self.sql["ebf_search"][7], {"graph_id": graph})

        # fetch start edge data
        start_edge = self.connection.execute(
            self.sql["ebf_search"][8], {"id": start_edge_id}
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

        def enter(vertex: tuple, graph: str, connection: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM, CYIM, CEIM):
                raise Exception(
                    f"cannot alter vertices/edges/cycles of '{graph}'"
                )

            # initialize all edges
            connection.execute(
                self.sql["minimum_spanning_tree"][0],
                {
                    "id": vertex[0],
                    "mst_key": self.inf,
                    "graph_id": graph,
                },
            )

        def loop_condition(graph: str, connection: object) -> bool:
            """"""
            return (
                0
                < connection.execute(
                    self.sql["minimum_spanning_tree"][1], {"graph_id": graph}
                ).scalar_one()
            )

        def pop(graph: str, connection: object) -> tuple:
            """"""
            return connection.execute(
                self.sql["minimum_spanning_tree"][2],
                {"graph_id": graph},
            ).fetchone()

        def adjacency(vertex: tuple, graph: str, connection: object) -> list:
            """"""
            return connection.execute(
                self.sql["minimum_spanning_tree"][3],
                {
                    "graph_id": graph,
                    "child_vertex_id": vertex[0],
                    "parent_vertex_id": vertex[0],
                },
            ).fetchall()

        def push(
            adj_vertex: tuple, vertex: tuple, graph: str, connection: object
        ) -> None:
            """"""
            weight = connection.execute(
                self.sql["minimum_spanning_tree"][4],
                {"id": vertex[0], "adj_id": adj_vertex[0]},
            ).scalar_one()
            if adj_vertex[3] == Color.WHITE and adj_vertex[2] > weight:
                connection.execute(
                    self.sql["minimum_spanning_tree"][5],
                    {
                        "predecessor": vertex[0],
                        "mst_key": weight,
                        "id": adj_vertex[0],
                    },
                )

        start_vertex = self.connection.execute(
            self.sql["minimum_spanning_tree"][6], {"id": start_vertex_id}
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

        def enter(vertex: tuple, graph: str, connection: object) -> None:
            """"""

            # check for immutability flags set
            if self.check_mode(graph, VEIM, EDIM):
                raise Exception(
                    f"cannot alter vertices/edges/cycles of '{graph}'"
                )

            # initialize all edges
            connection.execute(
                self.sql["single_source_shortest_path"][0],
                {"sp_estimate": self.inf, "graph_id": graph},
            )
            connection.execute(
                self.sql["single_source_shortest_path"][1], {"id": vertex[0]}
            )

        def loop_condition(graph: str, connection: object) -> bool:
            """"""
            return (
                0
                < connection.execute(
                    self.sql["single_source_shortest_path"][2],
                    {"graph_id": graph},
                ).fetchone()[0]
            )

        def pop(graph: str, connection: object) -> tuple:
            """"""
            next_vertex = connection.execute(
                self.sql["single_source_shortest_path"][3],
                {"graph_id": graph},
            ).fetchone()
            connection.execute(
                self.sql["single_source_shortest_path"][4],
                {"graph_id": graph, "id": next_vertex[0]},
            )
            return next_vertex

        def adjacency(vertex: tuple, graph: str, connection: object) -> list:
            """"""
            return connection.execute(
                self.sql["single_source_shortest_path"][5],
                {"graph_id": graph, "parent_vertex_id": vertex[0]},
            ).fetchall()

        def push(
            adj_vertex: tuple, vertex: tuple, graph: str, connection: object
        ) -> None:
            """"""
            weight = connection.execute(
                self.sql["single_source_shortest_path"][6],
                {
                    "graph_id": graph,
                    "parent_vertex_id": vertex[0],
                    "child_vertex_id": adj_vertex[0],
                },
            ).fetchone()
            if weight is None:
                raise Exception("no weight!")
            if adj_vertex[2] > vertex[2] + weight[0]:
                connection.execute(
                    self.sql["single_source_shortest_path"][7],
                    {
                        "predecessor": vertex[0],
                        "sp_estimate": vertex[2] + weight[0],
                        "id": adj_vertex[0],
                    },
                )

        start_vertex = self.connection.execute(
            self.sql["single_source_shortest_path"][8],
            {"id": start_vertex_id},
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
        self.connection.execute(
            self.sql["flow_network_walk_vbf"][0],
            {"bf_distance": self.inf, "graph_id": graph},
        )

        # initialize queue order paramter
        pushed = 0

        # fetch start vertex
        s = self.connection.execute(
            self.sql["flow_network_walk_vbf"][1],
            {"graph_id": graph, "id": source_vertex_id},
        ).fetchone()
        if s is None:
            raise Exception(
                f"vertex with id '{source_vertex_id}' not part of {graph}"
            )

        # push the vertex to start
        self.connection.execute(
            self.sql["flow_network_walk_vbf"][2],
            {"pushed": pushed, "graph_id": graph, "id": s[0]},
        )

        # while there are vertices to handle
        while (
            0
            < self.connection.execute(
                self.sql["flow_network_walk_vbf"][3], {"graph_id": graph}
            ).fetchone()[0]
        ):

            # fetch and dequeue the next vertex
            u = self.connection.execute(
                self.sql["flow_network_walk_vbf"][4], {"graph_id": graph}
            ).fetchone()
            self.connection.execute(
                self.sql["flow_network_walk_vbf"][5], {"id": u[0]}
            )

            # break early at sink
            if u[0] == sink_vertex_id:
                break

            # handle its descendents bf
            for v in self.connection.execute(
                self.sql["flow_network_walk_vbf"][6],
                {"parent_vertex_id": u[0]},
            ).fetchall():

                pushed += 1

                self.connection.execute(
                    self.sql["flow_network_walk_vbf"][7],
                    {
                        "predecessor": u[0],
                        "bf_distance": u[4] + 1,
                        "pushed": pushed,
                        "graph_id": graph,
                        "id": v[0],
                    },
                )

    def maximum_flow(
        self: object, graph: str, source_vertex_id: int, sink_vertex_id: int
    ) -> None:
        """"""

        # check for immutability flags set
        if self.check_mode(graph, VEIM, EDIM):
            raise Exception(f"cannot alter vertices/edges of '{graph}'")

        # set flows to zero
        self.connection.execute(
            self.sql["maximum_flow"][0], {"graph_id": graph}
        )

        def generate_edges():
            """"""
            chunk_cursor = self.connection.execute(
                self.sql["maximum_flow"][1], {"graph_id": graph}
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
            path = self.connection.execute(
                self.sql["maximum_flow"][2],
                {"id": sink_vertex_id, "predecessor": source_vertex_id},
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
                self.connection.execute(
                    self.sql["maximum_flow"][3],
                    {"mf_flow": f, "id": edge[0]},
                )
