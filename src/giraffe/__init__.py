from .logic import Color, Database, vertex_odict_factory, edge_odict_factory
from .logic import EDIM, VEIM, CYIM, CEIM
from .model import dql_map_raw, metadata

Database.sql = dql_map_raw
Database.metadata = metadata
