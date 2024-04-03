import sqlite3


def connect(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, isolation_level="EXCLUSIVE")
    con.execute("""PRAGMA foreign_keys = true""")
    con.commit()
    return con
