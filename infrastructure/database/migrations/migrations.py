import os

def _execute_sql_scripts(db_connection, directory, suffix_filter=None):
    scripts = [
        f for f in sorted(os.listdir(directory))
        if f.endswith('.sql') and 
           (suffix_filter is not None and f.endswith(suffix_filter) or
           suffix_filter is None and not f.endswith('database.sql'))
    ]

    with db_connection as conn:
        with conn.cursor() as cur:
            for filename in scripts:
                path = os.path.join(directory, filename)
                with open(path, 'r') as file:
                    raw_sql = file.read()
                    cur.execute(raw_sql)
                
                print(f"Executed {filename}")

        conn.commit()

def create_database(db_connection):
    directory = os.path.dirname(__file__)
    _execute_sql_scripts(db_connection, directory, suffix_filter='database.sql')

def run_migrations(db_connection):
    directory = os.path.dirname(__file__)
    _execute_sql_scripts(db_connection, directory)

def database_exists(db_connection, db_name):
    with db_connection.cursor() as cur:
        cur.execute("SELECT datname FROM pg_database")
        databases = [row['datname'] for row in cur.fetchall()]
        print(f"Databases: {databases}")
    return db_name in databases
