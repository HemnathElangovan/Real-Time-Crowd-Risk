"""
db.py
Reusable MySQL connection utilities for the Crowd Risk project.
"""

try:
    import mysql.connector
    from mysql.connector import Error
except Exception:  # mysql package missing
    mysql = None
    Error = Exception

import config


def get_connection():
    """
    Create and return a MySQL connection using environment-driven config.
    Returns None if connection fails.
    """
    if "mysql" in globals() and mysql is None:
        print("[DB] mysql-connector-python not installed. DB disabled.")
        return None

    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            database=config.MYSQL_DATABASE,
            autocommit=False,
        )
        return conn
    except Error as e:
        print(f"[DB] Connection error: {e}")
        return None
    except Exception as e:
        print(f"[DB] Unexpected connection error: {e}")
        return None


def safe_close(cursor=None, conn=None):
    """Safely close cursor and connection without raising cleanup errors."""
    try:
        if cursor is not None:
            cursor.close()
    except Exception:
        pass

    try:
        if conn is not None and conn.is_connected():
            conn.close()
    except Exception:
        pass
