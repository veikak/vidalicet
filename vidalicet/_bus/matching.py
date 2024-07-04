from typing import Sequence
from dataclasses import dataclass
from datetime import time

from .common import EcuBlockId, RawReading
from .. import _db, _log_parsing

MSG_TYPE_LEN = 2


@dataclass(frozen=True)
class _EcuBlockIdByCompVal:
    comp_val_len: int
    data: dict[str, EcuBlockId]


type _EcuBlockIdByCompValByCanAddr = dict[str, _EcuBlockIdByCompVal]


class MessageMatcher:
    _data: _EcuBlockIdByCompValByCanAddr

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
                self._data[d.can_id_rx] = _EcuBlockIdByCompVal(
                    comp_val_len=len(comp_val), data={}
                )
            else:
                # All compare values should be of the same length
                assert len(comp_val) == self._data[d.can_id_rx].comp_val_len

            # There should be no duplicate compare values
            assert comp_val not in self._data[d.can_id_rx].data

            self._data[d.can_id_rx].data[comp_val] = EcuBlockId(
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
            matched_id = comp_data.get(
                message.message[MSG_TYPE_LEN : MSG_TYPE_LEN + comp_val_len], None
            )
            if matched_id is None:
                continue

            yield RawReading(
                id=matched_id,
                payload=message.message[MSG_TYPE_LEN + comp_val_len :],
                time=message.time,
            )
