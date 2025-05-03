from .migrations.migrations import run_migrations, create_database, database_exists
from .utils.connection import get_db_connection
import os

def initialize_database():
    db_default_name = os.getenv('DB_DEFAULT_NAME')
    target_db_name = os.getenv('DB_NAME')

    try:
        admin_conn = get_db_connection(db_default_name)

        if not database_exists(admin_conn, target_db_name):
            print(f"Database {target_db_name} does not exist. Creating...")
            create_database(admin_conn)
            admin_conn.close()

            migration_conn = get_db_connection()
            run_migrations(migration_conn)
            migration_conn.close()
        else:
            print(f"Database {target_db_name} already exists. Skipping creation.")

    except Exception as e:
        print(f"Error during database initialization: {e}")

