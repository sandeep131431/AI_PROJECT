
from agent.database.connection import get_db_connection


def inspect_schema():

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            cur.execute("""
                SELECT
                    table_schema,
                    table_name,
                    column_name,
                    data_type
                FROM information_schema.columns
                WHERE table_schema IN ('audit', 'erp')
                ORDER BY
                    table_schema,
                    table_name,
                    ordinal_position;
            """)

            rows = cur.fetchall()

            current_table = None

            for schema, table, column, data_type in rows:

                table_name = f"{schema}.{table}"

                if current_table != table_name:
                    current_table = table_name
                    print(f"\n--- {table_name} ---")

                print(f"{column} : {data_type}")

    finally:
        conn.close()


if __name__ == "__main__":
    inspect_schema()
