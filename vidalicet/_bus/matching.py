from typing import Sequence
from dataclasses import dataclass
from datetime import time

from .. import _db, _log_parsing

MSG_TYPE_LEN = 2


@dataclass
class _IdByCompVal:
    comp_val_len: int
    data: dict[str, int]


type _IdByCompValByCanAddr = dict[str, _IdByCompVal]


@dataclass
class ParameterReading:
    parent_block_id: int
    payload: str
    time: time


class MessageMatcher:
    _data: _IdByCompValByCanAddr

    def __init__(self, match_datas: Sequence[_db.matching.DbParentBlockMatchData]):
        self._data = {}

        for d in match_datas:
            if not d.compare_value.startswith("0x"):
                raise ValueError(
                    f"Bad parent block compare value. Expected hex, got: '{d.compare_value}'"
                )

            # Strip 0x prefix
            comp_val = d.compare_value[2:]

            if d.can_id_rx not in self._data:
                # New CAN id: initialize mapping
                self._data[d.can_id_rx] = _IdByCompVal(
                    comp_val_len=len(comp_val), data={}
                )
            else:
                # All compare values should be of the same length
                assert len(comp_val) == self._data[d.can_id_rx].comp_val_len

            # There should be no duplicate compare values
            assert comp_val not in self._data[d.can_id_rx].data

            self._data[d.can_id_rx].data[comp_val] = d.block_id

    def match(
        self, message: _log_parsing.params.RawParamRxMsg
    ) -> ParameterReading | None:
        id_by_comp_val = self._data.get(message.ecu_addr, None)
        if not id_by_comp_val:
            return None

        comp_val_len = id_by_comp_val.comp_val_len
        data = id_by_comp_val.data

        # First MSG_TYPE_LEN chars: message type (ignored)
        # Next comp_val_len chars: parameter address (should match compare value)
        # Rest: payload
        matched_id = data.get(
            message.message[MSG_TYPE_LEN : MSG_TYPE_LEN + comp_val_len], None
        )
        if matched_id is None:
            return None

        return ParameterReading(
            parent_block_id=matched_id,
            payload=message.message[MSG_TYPE_LEN + comp_val_len :],
            time=time,
        )
