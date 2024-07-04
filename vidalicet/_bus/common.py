from dataclasses import dataclass
from datetime import time


@dataclass(frozen=True, order=True)
class EcuBlockId:
    ecu_variant_id: int
    parent_block_id: int


@dataclass(frozen=True)
class RawReading:
    id: EcuBlockId
    payload: str
    time: time


@dataclass(frozen=True)
class Reading:
    time: time
    value: int | float


@dataclass(frozen=True)
class ParameterReadings:
    block_id: int
    # parent_text: str
    name: str
    text: str
    ppe_text: str
    ppe_unit_text: str
    data: list[Reading]
