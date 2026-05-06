import pyodbc
import os
import dotenv

dotenv.load_dotenv()

def get_db_connection():
    try:
        conn = pyodbc.connect(
            f"DRIVER={os.getenv('db_driver', 'ODBC Driver 18 for SQL Server')};"
            f"SERVER={os.getenv('db_server')};"
            f"DATABASE={os.getenv('db_name', '')};"
            f"UID={os.getenv('db_readwrite_user', 'readwrite_user')};"
            f"PWD={os.getenv('db_readwrite_password', '')};"
            f"TrustServerCertificate={'yes'};"
        )
        return conn
    except Exception as e:
        print("Database connection error:", e)
        return None