import duckdb

DB_PATH = "my_database.db"


def setup():
    conn = duckdb.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id              INTEGER PRIMARY KEY,
            name            VARCHAR NOT NULL,
            original_stock  INTEGER NOT NULL,
            current_stock   INTEGER NOT NULL,
            doses_per_day   INTEGER NOT NULL CHECK (doses_per_day > 0),
            added_date      DATE    NOT NULL,
            finish_date     DATE    NOT NULL,
            restock_date    DATE    NOT NULL,
            is_active       BOOLEAN NOT NULL DEFAULT TRUE
        )
    """)
    conn.close()
    print("✅ medicines table ready.")


def get_next_id(conn):
    """Get next available ID manually."""
    row = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM medicines").fetchone()
    return row[0]


def get_connection():
    return duckdb.connect(DB_PATH)
