from psycopg2.extras import RealDictCursor
import psycopg2
import os

def get_db_connection(name = os.getenv('DB_NAME')):
    print("Connecting to the database...")
    conn = psycopg2.connect(
        dbname = name,
        host = os.getenv('DB_HOST'),
        port = os.getenv('DB_PORT'),
        user = os.getenv('DB_USER'),
        sslmode = os.getenv('SSL_MODE'),
        sslrootcert = os.getenv('SSL_DB_CA'),
        sslcert = os.getenv('SSL_DB_CLIENT_CERT'),
        sslkey = os.getenv('SSL_DB_CLIENT_KEY'),
        cursor_factory=RealDictCursor
    )
    return conn
