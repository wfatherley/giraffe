# `giraffe` -- a database-oriented library for handling graphs

<hr>

## TODOs
 - add test for find cycles to ensure "is cyclic" is updated correctly
 - try and break autoincrement for vertices and edges tables
 - build PEP-249 infra: find way to also pass dicts instead of tuples for database libraries that use only `:col_name` interpolation
 - re-evaluate how sql statements are stored and fetched, eg not | but maybe |= for dict based container building for each method
 - explore possible use of eg sqlalchemy rather than rolling your own
 - try and factor out a df_base, since both v and e are essentially the same
 - documentation (when above is done)

### PEP 249 notes and SQLAlchemy
Since the cursor object is specified in the PEP, cursors can be wrapped by a layer that always accepts a raw sql string and a tuple of parameters, which then performs the conversion to the specific interpolation type of the wrapped cursor. This would keep the dict-based sql statement store feasible

SQLAlchemy probably has a robust solution for this, which might be nice branch to build and evaluate

### dict sql store
This is what to do next. It decouples the methods from each other by centralizing each methods's sql statems to mutually exclusive lists

Note common dmls between minimum spanning tree and single source shortest path:

"""
        UPDATE vertex
        SET color = 2
        WHERE graph_id = ? AND id = ?
        """

"""
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = ? AND color = 0
        """

Note common dmls between vbf walk and flow netowrk walk vbf:

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
        """

"""
        UPDATE vertex
        SET color = 2, pushed = NULL
        WHERE id = ?
        """

"""
        SELECT id, tree, color, predecessor, bf_distance, pushed
        FROM vertex
        WHERE graph_id = ? AND pushed IS NOT NULL
        ORDER BY pushed ASC
        LIMIT 1
        """

"""
        SELECT COUNT(*)
        FROM vertex
        WHERE graph_id = ? AND pushed IS NOT NULL
        """

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
        """

"""
        SELECT id, tree, color, predecessor, bf_distance, pushed
        FROM vertex
        WHERE graph_id = ? AND id = ?
        LIMIT 1
        """

"""
        UPDATE vertex
        SET
            tree = NULL,
            color = 0,
            predecessor = NULL,
            bf_distance = ?,
            pushed = NULL
        WHERE graph_id = ?
        """

Note common dmls between vdf walk and transpose:

"SELECT id FROM vertex WHERE graph_id = ?"


### DF base
Both edge- and vertex-based DFS methods are basically the same except for the name of the "current object"-- either "edge" or "vertex". The main difference might be just the elements of the current object

 - the branch tips parameters are swapped in the very first query for branch tips and all other brancht tips queries
 - queries for new stack top during pop loop vary in size by two parameters

Seems like dropping into a function might be possible just like bf base, but seems overly complex