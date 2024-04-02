from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True, order=True)
class EcuBlockId:
    ecu_variant_id: int
    parent_block_id: int


@dataclass(frozen=True)
class ParameterReading:
    id: EcuBlockId
    payload: str
    time: time


@dataclass(frozen=True)
class ChildReading:
    block_id: int
    time: time
    value: int | float
