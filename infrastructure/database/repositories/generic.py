from infrastructure.database.utils.connection import get_db_connection

class GenericRepository:
    def __init__(self, table_name):
        self.table_name = table_name

    def insert(self, data: dict):
        keys = data.keys()
        values = data.values()
        columns = ','.join(keys)
        placeholders = ','.join(['%s'] * len(values))
        
        query = f"INSERT INTO {self.table_name} ({columns}) VALUES ({placeholders}) RETURNING *"
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                inserted_record = cur.fetchone()
                conn.commit()
                return inserted_record


    def find_by(self, conditions: dict, page: int = 1, size: int = 10):
        if not conditions:
            raise ValueError("Conditions dictionary cannot be empty")

        clause_parts = [f"{key} = %s" for key in conditions]
        where_clause = " AND ".join(clause_parts)
        values = list(conditions.values())

        offset = (page - 1) * size
        query = f"SELECT * FROM {self.table_name} WHERE {where_clause} LIMIT %s OFFSET %s"

        values.extend([size, offset])

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                return cur.fetchall()
            
    def update_by(self, conditions: dict, updates: dict):
        if not conditions:
            raise ValueError("Conditions dictionary cannot be empty")
        if not updates:
            raise ValueError("Updates dictionary cannot be empty")

        set_clause = ", ".join([f"{key} = %s" for key in updates])
        where_clause = " AND ".join([f"{key} = %s" for key in conditions])

        query = f"UPDATE {self.table_name} SET {set_clause} WHERE {where_clause}"

        values = tuple(updates.values()) + tuple(conditions.values())

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                conn.commit()

    def delete_by(self, conditions: dict):
        if not conditions:
            raise ValueError("Conditions dictionary cannot be empty")

        clause_parts = [f"{key} = %s" for key in conditions]
        where_clause = " AND ".join(clause_parts)
        values = tuple(conditions.values())

        query = f"DELETE FROM {self.table_name} WHERE {where_clause}"

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(query, values)
                conn.commit()
