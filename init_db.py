"""
init_db.py
Initialize MySQL tables for the Crowd Risk project.

Run:
    python init_db.py
"""

import mysql.connector
from mysql.connector import Error

import config
from db import safe_close


def ensure_database():
    """Create database if missing, then close bootstrap connection."""
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(
            host=config.MYSQL_HOST,
            port=config.MYSQL_PORT,
            user=config.MYSQL_USER,
            password=config.MYSQL_PASSWORD,
            autocommit=True,
        )
        cursor = conn.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{config.MYSQL_DATABASE}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        print(f"[DB] Database ensured: {config.MYSQL_DATABASE}")
    except Error as e:
        print(f"[DB] Failed to create database: {e}")
        raise
    finally:
        safe_close(cursor, conn)


def create_tables():
    """Create all app tables if they do not exist."""
    from db import get_connection

    conn = get_connection()
    if conn is None:
        raise RuntimeError("[DB] Cannot initialize tables: connection unavailable.")

    cursor = None
    try:
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                id INT AUTO_INCREMENT PRIMARY KEY,
                camera_name VARCHAR(100) NOT NULL,
                camera_source VARCHAR(255) NOT NULL,
                location_name VARCHAR(150),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_camera_source (camera_source)
            ) ENGINE=InnoDB
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS crowd_events (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                camera_id INT NOT NULL,
                person_count INT NOT NULL,
                risk_level ENUM('LOW','MEDIUM','HIGH') NOT NULL,
                event_time DATETIME NOT NULL,
                snapshot_path VARCHAR(255),
                fps DECIMAL(6,2),
                notes VARCHAR(255) NULL,
                CONSTRAINT fk_crowd_camera
                    FOREIGN KEY (camera_id) REFERENCES cameras(id)
                    ON DELETE RESTRICT ON UPDATE CASCADE,
                INDEX idx_crowd_time (event_time),
                INDEX idx_crowd_camera_time (camera_id, event_time)
            ) ENGINE=InnoDB
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS alert_logs (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                camera_id INT NOT NULL,
                risk_level ENUM('LOW','MEDIUM','HIGH') NOT NULL,
                alert_type ENUM('WHATSAPP','EMAIL','SOUND') NOT NULL,
                recipient VARCHAR(150),
                status ENUM('SUCCESS','FAILED') NOT NULL,
                message_sid VARCHAR(100),
                error_message TEXT,
                alert_time DATETIME NOT NULL,
                CONSTRAINT fk_alert_camera
                    FOREIGN KEY (camera_id) REFERENCES cameras(id)
                    ON DELETE RESTRICT ON UPDATE CASCADE,
                INDEX idx_alert_time (alert_time),
                INDEX idx_alert_camera_time (camera_id, alert_time)
            ) ENGINE=InnoDB
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                id INT AUTO_INCREMENT PRIMARY KEY,
                setting_key VARCHAR(100) UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB
            """
        )

        conn.commit()
        print("[DB] Tables ensured successfully.")
    except Error as e:
        conn.rollback()
        print(f"[DB] Table creation failed: {e}")
        raise
    finally:
        safe_close(cursor, conn)


if __name__ == "__main__":
    ensure_database()
    create_tables()
    print("[DB] Initialization completed.")
