from typing import Sequence, List, Protocol, ClassVar, Any
from sqlite3 import Connection
import dataclasses

from . import _common


@dataclasses.dataclass
class DbChildBlockSpec:
    id: int
    length: int
    offset: int
    data_type: str
    scaling: str
    ppe_scaling: str


_db_child_block_spec_factory = _common.create_dataclass_row_factory(DbChildBlockSpec)


def get_child_block_specs(
    con: Connection, ecu_variant_id: int, parent_block_id: int
) -> List[DbChildBlockSpec]:
    cur = con.cursor()
    cur.row_factory = _db_child_block_spec_factory
    return cur.execute(
        f"""
        SELECT
            ecu_blocks.child_block_id as id
            , blocks.length
            , blocks.offset
            , data_types.name as data_type
            , scalings.definition as scaling
            , scalings_ppe.definition as ppe_scaling
        FROM ecu_variant_block_trees ecu_blocks
        INNER JOIN blocks
            ON blocks.id = ecu_blocks.child_block_id
        INNER JOIN block_values
            ON block_values.block_id = blocks.id
        INNER JOIN data_types
            ON data_types.id = blocks.data_type_id
        INNER JOIN scalings
            ON scalings.id = block_values.scaling_id
        INNER JOIN scalings scalings_ppe
            ON scalings_ppe.id = block_values.ppe_scaling_id
        WHERE
            ecu_blocks.ecu_variant_id = :ecu_variant_id
            AND ecu_blocks.parent_block_id = :parent_block_id
        """,
        {"ecu_variant_id": ecu_variant_id, "parent_block_id": parent_block_id},
    ).fetchall()
