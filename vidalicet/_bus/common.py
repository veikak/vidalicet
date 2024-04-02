from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True, order=True)
class EcuBlockId:
    ecu_variant_id: int
    parent_block_id: int


@dataclass
class ParameterReading:
    id: EcuBlockId
    payload: str
    time: time


@dataclass
class ChildReading:
    block_id: int
    time: time
    value: int | float
