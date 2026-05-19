"""DB migration for inventory-api. Called by K8s Job: python -m app.migrate"""
import os
import sys
import logging
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "inventory_db")
DB_USER = os.getenv("DB_USER", "klight")
DB_PASSWORD = os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "klight"))


def get_conn(dbname=None):
    return psycopg2.connect(
        host=DB_HOST, port=DB_PORT,
        dbname=dbname or DB_NAME,
        user=DB_USER, password=DB_PASSWORD,
    )


def ensure_db():
    conn = get_conn(dbname="postgres")
    conn.autocommit = True
    with conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DB_NAME,))
        if not cur.fetchone():
            cur.execute(f"CREATE DATABASE {DB_NAME}")
            logger.info("Created database %s", DB_NAME)
    conn.close()


V1_SQL = """
CREATE TABLE IF NOT EXISTS stock (
    id SERIAL PRIMARY KEY,
    product_id INTEGER UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0
);

INSERT INTO stock (product_id, name, quantity) VALUES
    (1, 'Widget A', 10),
    (2, 'Widget B', 5),
    (3, 'Widget C', 20)
ON CONFLICT (product_id) DO NOTHING;
"""


def run():
    ensure_db()
    conn = get_conn()
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            logger.info("Running inventory-api migration v1")
            cur.execute(V1_SQL)
        logger.info("Migration complete")
    finally:
        conn.close()


if __name__ == "__main__":
    run()
