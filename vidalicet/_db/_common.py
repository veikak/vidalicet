import dataclasses
import sqlite3


def create_dataclass_row_factory(dc: object):
    fields = dataclasses.fields(dc)

    def factory(cursor: sqlite3.Cursor, row: tuple):
        for i, field in enumerate(fields):
            column_name = cursor.description[i][0]
            assert column_name == field.name
            assert isinstance(row[i], field.type)
        return dc(*row)

    return factory
