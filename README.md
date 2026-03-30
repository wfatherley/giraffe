# `giraffe` -- a database-oriented library for handling graphs

<hr>


```sql
WITH RECURSIVE
    path_edges AS (
        SELECT
            e.id, e.mf_capacity, e.mf_flow, e.metadata, e.parent_vertex_id
        FROM
            edge AS e
        WHERE
            e.id = (
                SELECT id
                FROM edge
                WHERE
                    child_vertex_id = ?
                    e.mf_flow < e.mf_capacity
                    COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
                LIMIT 1
            )
        UNION ALL
        SELECT
            e.id, e.mf_capacity, e.mf_flow, e.metadata, e.parent_vertex_id
        FROM
            edge AS e
        JOIN
            path_edges AS pv
            ON pe.parent_vertex_id = e.child_vertex_id
        WHERE
            e.mf_flow < e.mf_capacity
            AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
            --AND e.parent_vertex_id = (SELECT predecessor FROM vertex WHERE id = ?)
    )
SELECT id, mf_capacity, mf_flow, metadata
FROM path_edges
    
-----------------------
WITH RECURSIVE
                    path_vertices AS (
                        SELECT id, predecessor FROM vertex WHERE id = ?
                        UNION ALL
                        SELECT v.id, v.predecessor FROM vertex AS v
                        JOIN path_vertices AS pv ON v.id = pv.predecessor
                        JOIN edge AS e ON e.parent_vertex_id = pv.predecessor AND e.child_vertex_id = v.id
                        WHERE e.mf_flow < e.mf_capacity AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
                    )
                SELECT
                    e.id, e.mf_capacity, e.mf_flow, e.metadata
                FROM
                    edge AS e
                JOIN
                    path_vertices AS pv
                        ON e.parent_vertex_id = pv.predecessor
                        AND e.child_vertex_id = pv.id
               WHERE
                   e.graph_id = ?
                   AND e.mf_flow < e.mf_capacity
                   AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
-------------------------

WITH RECURSIVE
    path_vertices AS (
        SELECT id, predecessor FROM vertex WHERE id = ?
        UNION ALL
        SELECT v.id, v.predecessor FROM vertex AS v
        JOIN path_vertices AS pv ON v.id = pv.predecessor
        JOIN edge AS e ON e.parent_vertex_id = pv.predecessor AND e.child_vertex_id = v.id
        WHERE e.mf_flow < e.mf_capacity AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
    )
SELECT
    e.id, e.mf_capacity, e.mf_flow, e.metadata
FROM
    edge AS e
JOIN
    path_vertices AS pv
        ON e.parent_vertex_id = pv.predecessor
        AND e.child_vertex_id = pv.id
WHERE
    e.graph_id = ?
    AND e.mf_flow < e.mf_capacity
    AND COALESCE(e.metadata, '') NOT LIKE '%"hiding" = true%'
```