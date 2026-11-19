
import os

import psycopg
from dotenv import load_dotenv


load_dotenv()


def get_db_connection():

    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise ValueError("DATABASE_URL not found in .env")

    connection = psycopg.connect(database_url)

    return connection


if __name__ == "__main__":

    try:
        conn = get_db_connection()

        print("Neon PostgreSQL Connected Successfully!")

        conn.close()

    except Exception as error:
        print("Database Connection Failed:", error)
