import duckdb

DB_PATH = "my_database.db"


def setup():
    conn = duckdb.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id            INTEGER PRIMARY KEY,
            name          VARCHAR NOT NULL,
            stock_qty     INTEGER NOT NULL CHECK (stock_qty >= 0),
            doses_per_day INTEGER NOT NULL CHECK (doses_per_day > 0),
            added_date    DATE    NOT NULL,
            finish_date   DATE    NOT NULL,
            restock_date  DATE    NOT NULL
        )
    """)
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS medicine_id_seq START 1
    """)
    conn.close()
    print("✅ medicines table ready.")


def get_connection():
    return duckdb.connect(DB_PATH)
