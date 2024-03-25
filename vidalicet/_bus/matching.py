from typing import Sequence
from dataclasses import dataclass
from datetime import time

from .. import _db, _log_parsing

MSG_TYPE_LEN = 2


@dataclass
class _IdPair:
    parent_block_id: int
    ecu_variant_id: int


@dataclass
class _IdPairByCompVal:
    comp_val_len: int
    data: dict[str, _IdPair]


type _IdPairByCompValByCanAddr = dict[str, _IdPairByCompVal]


@dataclass
class ParameterReading:
    parent_block_id: int
    ecu_variant_id: int
    payload: str
    time: time


class MessageMatcher:
    _data: _IdPairByCompValByCanAddr

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
                self._data[d.can_id_rx] = _IdPairByCompVal(
                    comp_val_len=len(comp_val), data={}
                )
            else:
                # All compare values should be of the same length
                assert len(comp_val) == self._data[d.can_id_rx].comp_val_len

            # There should be no duplicate compare values
            assert comp_val not in self._data[d.can_id_rx].data

            self._data[d.can_id_rx].data[comp_val] = _IdPair(
                parent_block_id=d.block_id, ecu_variant_id=d.ecu_variant_id
            )

    def match(self, messages: Sequence[_log_parsing.params.RawParamRxMsg]):
        for message in messages:
            id_pair_by_comp_val = self._data.get(message.ecu_addr, None)
            if not id_pair_by_comp_val:
                continue

            comp_val_len = id_pair_by_comp_val.comp_val_len
            comp_data = id_pair_by_comp_val.data

            # First MSG_TYPE_LEN chars: message type (ignored)
            # Next comp_val_len chars: parameter address (should match compare value)
            # Rest: payload
            matched_id_pair = comp_data.get(
                message.message[MSG_TYPE_LEN : MSG_TYPE_LEN + comp_val_len], None
            )
            if matched_id_pair is None:
                continue

            yield ParameterReading(
                parent_block_id=matched_id_pair.parent_block_id,
                ecu_variant_id=matched_id_pair.ecu_variant_id,
                payload=message.message[MSG_TYPE_LEN + comp_val_len :],
                time=time,
            )
