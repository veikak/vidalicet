from typing import Sequence, List, Protocol, ClassVar, Any
from sqlite3 import Connection
import dataclasses

from . import _common


@dataclasses.dataclass
class DbParentBlockMatchData:
    block_id: int
    ecu_variant_id: int
    can_id_rx: str
    compare_value: str


_db_parent_block_match_data_factory = _common.create_dataclass_row_factory(
    DbParentBlockMatchData
)


def get_parent_match_data(
    con: Connection, ecu_identifiers: Sequence[str]
) -> List[DbParentBlockMatchData]:
    if len(ecu_identifiers) == 0:
        return []

    ecu_identifier_placeholders = ", ".join(("?" for _ in range(len(ecu_identifiers))))
    cur = con.cursor()
    cur.row_factory = _db_parent_block_match_data_factory
    return cur.execute(
        f"""
        SELECT DISTINCT
            blocks_p.id as block_id
            , ecu_blocks.ecu_variant_id
            , ecus.can_id_rx
            , block_values_p.compare_value
        FROM ecu_variants ecus
        LEFT JOIN ecu_variant_block_trees ecu_blocks
            ON ecu_blocks.ecu_variant_id = ecus.id
        INNER JOIN blocks blocks_p
            ON blocks_p.id = ecu_blocks.parent_block_id
        INNER JOIN block_values block_values_p
            ON block_values_p.block_id = blocks_p.id
        WHERE ecus.identifier IN ({ecu_identifier_placeholders})
        """,
        tuple(ecu_identifiers),
    ).fetchall()
