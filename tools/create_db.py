from typing import TextIO
import sqlite3
import argparse
import os.path
import contextlib
import csv
import logging

logger = logging.getLogger(__name__)


def create_texts(con: sqlite3.Connection, dump: TextIO) -> None:
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE texts (
            id INTEGER PRIMARY KEY ASC,
            data TEXT NOT NULL
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT INTO texts (
            id,
            data
        )
        VALUES (
            :text_id,
            :data
        )
        """,
        reader,
    )
    con.commit()


def create_scalings(con: sqlite3.Connection, dump: TextIO) -> None:
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE scalings (
            id INTEGER PRIMARY KEY ASC,
            definition TEXT NOT NULL
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT INTO scalings (
            id,
            definition
        )
        VALUES (
            :id,
            :definition
        )
        """,
        reader,
    )
    con.commit()


def create_data_types(con: sqlite3.Connection, dump: TextIO):
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE data_types (
            id INTEGER PRIMARY KEY ASC,
            name TEXT NOT NULL
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT INTO data_types (
            id,
            name
        )
        VALUES (
            :id,
            :name
        )
        """,
        reader,
    )
    con.commit()


def create_blocks(con: sqlite3.Connection, dump: TextIO):
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE blocks (
            id INTEGER PRIMARY KEY ASC,
            name TEXT,
            name_text_id INTEGER REFERENCES texts(id) NOT NULL,
            data_type_id INTEGER REFERENCES data_types(id) NOT NULL,
            offset INTEGER NOT NULL,
            length INTEGER NOT NULL
        )
        STRICT
        """
    )
    con.commit()
    converted_rows = (
        {**row, "offset": row["offset"] if row["offset"] != "" else 0} for row in reader
    )
    con.executemany(
        """
        INSERT INTO blocks (
            id,
            name,
            name_text_id,
            data_type_id,
            offset,
            length
        )
        VALUES (
            :id,
            :name,
            :name_text_id,
            :data_type_id,
            :offset,
            :length
        )
        """,
        converted_rows,
    )
    con.commit()


# def parse_compare_value(value: str) -> bytes | None:
#     match value:
#         case "":
#             return None
#         case s if s.startswith("0x"):
#             nibbles = value[2:]
#             nibbles_sane = f"0{nibbles}" if len(nibbles) % 2 != 0 else nibbles
#             try:
#                 bytes.fromhex(nibbles_sane)
#             except ValueError:
#                 print(nibbles, nibbles_sane)
#             return bytes.fromhex(nibbles_sane)
#         case s if s.startswith("0b"):
#             bits = value[2:]
#             mod = len(bits) % 8
#             pad_count = 0 if mod == 0 else 8 - mod
#             padded_bits = f"{"0" * pad_count}{bits}"
#             as_ints = (
#                 int(byte_bits, base=2)
#                 for byte_bits in map("".join, list(zip(*[iter(padded_bits)] * 8)))
#             )
#             return bytes(as_ints)
#         case s if "." in s:
#             # Float
#             return None
#         case s if "-" in s:
#             # Signed int
#             return None
#         case _:
#             # Int
#             return None


def create_block_values(con: sqlite3.Connection, dump: TextIO):
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE block_values (
            block_id INTEGER REFERENCES blocks(id) NOT NULL,
            compare_value TEXT,
            scaling_id INTEGER REFERENCES scalings(id) NOT NULL,
            ppe_scaling_id INTEGER REFERENCES scalings(id) NOT NULL,
            text_id INTEGER REFERENCES texts(id) NOT NULL,
            ppe_text_id INTEGER REFERENCES texts(id) NOT NULL,
            ppe_unit_text_id INTEGER REFERENCES texts(id) NOT NULL,
            sort_order INTEGER NOT NULL
            --UNIQUE (block_id, compare_value, ppe_scaling_id)
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT INTO block_values (
            block_id,
            compare_value,
            scaling_id,
            ppe_scaling_id,
            text_id,
            ppe_text_id,
            ppe_unit_text_id,
            sort_order
        )
        VALUES (
            :block_id,
            :compare_value,
            :scaling_id,
            :ppe_scaling_id,
            :text_id,
            :ppe_text_id,
            :ppe_unit_text_id,
            :sort_order
        )
        """,
        reader,
    )
    con.commit()


def create_ecu_types(con: sqlite3.Connection, dump: TextIO):
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE ecu_types (
            id INTEGER PRIMARY KEY ASC,
            description TEXT NOT NULL
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT INTO ecu_types (
            id,
            description
        )
        VALUES (
            :id,
            :description
        )
        """,
        reader,
    )
    con.commit()


def create_ecu_variants(con: sqlite3.Connection, dump: TextIO):
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE ecu_variants (
            id INTEGER PRIMARY KEY ASC,
            ecu_type_id INTEGER REFERENCES ecu_types(id) NOT NULL,
            identifier TEXT UNIQUE NOT NULL,
            can_id_rx TEXT NOT NULL
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT INTO ecu_variants (
            id,
            ecu_type_id,
            identifier,
            can_id_rx
        )
        VALUES (
            :id,
            :ecu_type_id,
            :identifier,
            :can_id_rx
        )
        """,
        reader,
    )
    con.commit()


def create_ecu_variant_block_trees(con: sqlite3.Connection, dump: TextIO):
    reader = csv.DictReader(dump)
    con.execute(
        """
        CREATE TABLE ecu_variant_block_trees (
            ecu_variant_id INTEGER REFERENCES ecu_variants(id),
            parent_block_id INTEGER REFERENCES blocks(id),
            child_block_id INTEGER REFERENCES blocks(id),
            PRIMARY KEY (ecu_variant_id, parent_block_id, child_block_id)
        )
        STRICT
        """
    )
    con.commit()
    con.executemany(
        """
        INSERT OR IGNORE INTO ecu_variant_block_trees (
            ecu_variant_id,
            parent_block_id,
            child_block_id
        )
        VALUES (
            :ecu_variant_id,
            :parent_block_id,
            :child_block_id
        )
        """,
        reader,
    )
    con.commit()


creator_funcs = (
    ("texts", create_texts),
    ("scalings", create_scalings),
    ("data_types", create_data_types),
    ("blocks", create_blocks),
    ("block_values", create_block_values),
    ("ecu_types", create_ecu_types),
    ("ecu_variants", create_ecu_variants),
    ("ecu_variant_block_trees", create_ecu_variant_block_trees),
)


@contextlib.contextmanager
def open_dump_files(dump_dir: str):
    files = {
        name: open(os.path.join(dump_dir, f"{name}.csv"), "r", encoding="utf-8-sig")
        for name, _ in creator_funcs
    }
    try:
        yield files
    finally:
        for f in files.values():
            f.close()


def main():
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    arg_parser = argparse.ArgumentParser(
        description="Create an SQLite database from a CSV dump of Vida's database."
    )
    arg_parser.add_argument("dump_dir", help="path to directory containing .csv files")
    args = arg_parser.parse_args()

    con = sqlite3.connect("vidalicet.sqlite3", autocommit=False)

    with open_dump_files(args.dump_dir) as dump_files:
        for name, creator_func in creator_funcs:
            logger.info(f"Creating table '{name}'...")
            creator_func(con, dump_files[name])

    con.commit()
    con.close()


main()
