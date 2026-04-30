from .logic import (
    _Giraffe as Giraffe,
    Color,
    vertex_odict_factory,
    edge_odict_factory,
)
from .logic import EDIM, VEIM, CYIM, CEIM
from .model import dql_map_raw, metadata

Giraffe.sql = dql_map_raw
Giraffe.metadata = metadata
