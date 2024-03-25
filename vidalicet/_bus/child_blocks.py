from typing import Sequence
import sqlite3
import struct
from dataclasses import dataclass
from datetime import time

# import functools

from . import matching
from .. import _db

type ParentId = int
type ChildId = int


@dataclass
class ConvertedReading:
    block_id: int
    time: time
    value: int | float


# @functools.cache
def _get_unpack_format(value: bytes, data_type: str) -> str | None:
    value_len = len(value)
    match data_type:
        case "Signed":
            match value_len:
                case 1:
                    return ">b"
                case 2:
                    return ">h"
                case 4:
                    return ">i"
                case _:
                    return None
        case "Unsigned":
            match value_len:
                case 1:
                    return ">B"
                case 2:
                    return ">H"
                case 4:
                    return ">I"
                case _:
                    return None
        case "4-byte float":
            return ">f"
        case _:
            return None


# @functools.cache
def _from_hex(value: str, data_type: str) -> int | float | None:
    value_bytes = bytes.fromhex(value)
    unpack_format = _get_unpack_format(value_bytes, data_type)
    return struct.unpack(unpack_format, value_bytes)[0] if unpack_format else None


class BlockExtractor:
    _con: sqlite3.Connection
    _data: dict[ParentId, list[_db.child_blocks.DbChildBlockSpec]]

    def __init__(self, con: sqlite3.Connection) -> None:
        self._con = con
        self._data = {}

    def _fetch_child_specs(self, reading: matching.ParameterReading):
        return _db.child_blocks.get_child_block_specs(
            self._con,
            ecu_variant_id=reading.ecu_variant_id,
            parent_block_id=reading.parent_block_id,
        )

    def extract_children(
        self, readings: Sequence[matching.ParameterReading]
    ) -> list[ConvertedReading]:
        readings_list = list(readings)
        result = []

        for r in readings_list:
            if r.parent_block_id not in self._data:
                child_specs = self._fetch_child_specs(r)
                self._data[r.parent_block_id] = child_specs
            for spec in self._data[r.parent_block_id]:
                if spec.length % 8 != 0:
                    continue
                length_nibbles = spec.length // 4
                offset_nibbles = spec.offset // 4
                hex_value = r.payload[offset_nibbles : offset_nibbles + length_nibbles]
                value = _from_hex(value=hex_value, data_type=spec.data_type)
                if value is None:
                    continue
                result.append(
                    ConvertedReading(block_id=spec.id, time=r.time, value=value)
                )
        return result
