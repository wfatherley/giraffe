""""""
from .logic import _Giraffe as Giraffe, Color
from .logic import EDIM, VEIM, CYIM, CEIM
from .model import dql_map_raw, metadata

Giraffe.sql = dql_map_raw
Giraffe.metadata = metadata
