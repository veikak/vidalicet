from typing import Sequence
import sqlite3
import struct
from dataclasses import dataclass
from datetime import time
from itertools import groupby
import math

from . import matching
from .. import _db

type ParentId = int
type ChildId = int


@dataclass(frozen=True, order=True)
class EcuBlockId:
    ecu_variant_id: int
    parent_block_id: int


@dataclass
class ConvertedReading:
    block_id: int
    time: time
    value: int | float


def next_pow2(val: int):
    a = int(math.log2(val))
    if 2**a == val:
        return val
    return 2 ** (a + 1)


def _get_unpack_info(data_type: str, len_bytes: int) -> tuple[str, int] | None:
    """Returns `(unpack_format, padding)`."""
    match data_type:
        case "Signed":
            match len_bytes:
                case 1:
                    return (">b", 0)
                case 2:
                    return (">h", 0)
                case 4:
                    return (">i", 0)
                case _:
                    return None
        case "Unsigned":
            padded_len = next_pow2(len_bytes)
            padding = padded_len - len_bytes
            match padded_len:
                case 1:
                    return (">B", padding)
                case 2:
                    return (">H", padding)
                case 4:
                    return (">I", padding)
                case _:
                    return None
        case "4-byte float":
            return (">f", 0)
        case _:
            return None


def _from_hex(
    values: Sequence[str], unpack_format: str, padding: int
) -> list[int] | list[float]:
    padding_str = "00" * padding
    values_bytes = bytes.fromhex(padding_str + padding_str.join(values))
    return [x for (x,) in struct.iter_unpack(unpack_format, values_bytes)]


def _reading_to_ecu_block_id(r: matching.ParameterReading) -> EcuBlockId:
    return EcuBlockId(
        ecu_variant_id=r.ecu_variant_id, parent_block_id=r.parent_block_id
    )


class BlockExtractor:
    _con: sqlite3.Connection
    _data: dict[EcuBlockId, list[_db.child_blocks.DbChildBlockSpec]]

    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con
        self._data = {}

    def _fetch_child_specs(self, eb_id: EcuBlockId):
        return _db.child_blocks.get_child_block_specs(
            self._con,
            ecu_variant_id=eb_id.ecu_variant_id,
            parent_block_id=eb_id.parent_block_id,
        )

    def extract_children(
        self, readings: Sequence[matching.ParameterReading]
    ) -> list[ConvertedReading]:

        ## Group by parent
        sorted_readings = sorted(readings, key=_reading_to_ecu_block_id)
        groups = [
            (eb_id, list(readings))
            for eb_id, readings in groupby(sorted_readings, _reading_to_ecu_block_id)
        ]

        ## Fill in any missing child specs
        for eb_id, _ in groups:
            if eb_id not in self._data:
                child_specs = self._fetch_child_specs(eb_id)
                self._data[eb_id] = child_specs

        ## Convert
        result = []
        for eb_id, readings in groups:
            for spec in self._data[eb_id]:
                if spec.length % 8 != 0:
                    continue
                length_nibbles = spec.length // 4
                offset_nibbles = spec.offset // 4
                unpack_info = _get_unpack_info(spec.data_type, length_nibbles // 2)
                if not unpack_info:
                    continue
                hex_values = [
                    r.payload[offset_nibbles : offset_nibbles + length_nibbles]
                    for r in readings
                ]
                unpack_format, padding = unpack_info
                converted_values = _from_hex(
                    values=hex_values,
                    unpack_format=unpack_format,
                    padding=padding,
                )
                assert len(hex_values) == len(converted_values)
                for r, converted_value in zip(readings, converted_values):
                    if converted_value is None:
                        continue
                    result.append(
                        ConvertedReading(
                            block_id=spec.id, time=r.time, value=converted_value
                        )
                    )

        return result
