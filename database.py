import duckdb

DB_PATH = "my_database.db"


def setup():
    conn = duckdb.connect(DB_PATH)

    # Drop old table if exists to apply new schema (only in dev)
    # In production you'd use ALTER TABLE instead
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

    # Add columns if they don't exist (for existing databases)
    try:
        conn.execute("ALTER TABLE medicines ADD COLUMN original_stock INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE medicines ADD COLUMN current_stock INTEGER DEFAULT 0")
    except: pass
    try:
        conn.execute("ALTER TABLE medicines ADD COLUMN is_active BOOLEAN DEFAULT TRUE")
    except: pass

    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS medicine_id_seq START 1
    """)
    conn.close()
    print("✅ medicines table ready.")


def get_connection():
    return duckdb.connect(DB_PATH)
