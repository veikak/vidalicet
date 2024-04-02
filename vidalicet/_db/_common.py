from typing import TYPE_CHECKING, TypeVar
import dataclasses
import sqlite3

# https://github.com/python/typing_extensions/issues/115#issuecomment-1468150876
if TYPE_CHECKING:
    from _typeshed import DataclassInstance

DataclassT = TypeVar("DataclassT", bound="DataclassInstance")


def create_dataclass_row_factory(dc: type[DataclassT]):
    fields = dataclasses.fields(dc)

    def factory(cursor: sqlite3.Cursor, row: sqlite3.Row):
        for i, field in enumerate(fields):
            column_name = cursor.description[i][0]
            assert column_name == field.name
            assert isinstance(row[i], field.type)
        return dc(*row)

    return factory
