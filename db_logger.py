"""
db_logger.py
Helper functions to write/read operational data in MySQL.
"""

from datetime import datetime

try:
    from mysql.connector import Error
except Exception:
    Error = Exception

from db import get_connection, safe_close


def register_camera(camera_name, camera_source, location_name=None):
    """
    Insert camera if not present (by source), return DB camera id.
    Returns None on failure.
    """
    conn = get_connection()
    if conn is None:
        print("[DB] register_camera skipped: DB unavailable")
        return None

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id FROM cameras WHERE camera_source = %s LIMIT 1",
            (str(camera_source),),
        )
        row = cursor.fetchone()
        if row:
            camera_id = row[0]
            cursor.execute(
                """
                UPDATE cameras
                SET camera_name = %s, location_name = %s, is_active = TRUE
                WHERE id = %s
                """,
                (camera_name, location_name, camera_id),
            )
            conn.commit()
            print(f"[DB] Camera exists: id={camera_id}, name={camera_name}")
            return camera_id

        cursor.execute(
            """
            INSERT INTO cameras (camera_name, camera_source, location_name, is_active)
            VALUES (%s, %s, %s, TRUE)
            """,
            (camera_name, str(camera_source), location_name),
        )
        conn.commit()
        camera_id = cursor.lastrowid
        print(f"[DB] Camera registered: id={camera_id}, name={camera_name}")
        return camera_id
    except Error as e:
        conn.rollback()
        print(f"[DB] register_camera error: {e}")
        return None
    finally:
        safe_close(cursor, conn)


def log_crowd_event(camera_id, person_count, risk_level, snapshot_path=None, fps=None, notes=None):
    """Store one crowd event row."""
    if camera_id is None:
        return False

    conn = get_connection()
    if conn is None:
        print("[DB] log_crowd_event skipped: DB unavailable")
        return False

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO crowd_events
            (camera_id, person_count, risk_level, event_time, snapshot_path, fps, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (
                camera_id,
                int(person_count),
                risk_level,
                datetime.now(),
                snapshot_path,
                float(fps) if fps is not None else None,
                notes,
            ),
        )
        conn.commit()
        print(
            f"[DB] Crowd event logged: camera_id={camera_id}, "
            f"count={person_count}, risk={risk_level}"
        )
        return True
    except Error as e:
        conn.rollback()
        print(f"[DB] log_crowd_event error: {e}")
        return False
    finally:
        safe_close(cursor, conn)


def log_alert(camera_id, risk_level, alert_type, recipient, status, message_sid=None, error_message=None):
    """Store one alert attempt row."""
    if camera_id is None:
        return False

    conn = get_connection()
    if conn is None:
        print("[DB] log_alert skipped: DB unavailable")
        return False

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO alert_logs
            (camera_id, risk_level, alert_type, recipient, status, message_sid, error_message, alert_time)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                camera_id,
                risk_level,
                alert_type,
                recipient,
                status,
                message_sid,
                error_message,
                datetime.now(),
            ),
        )
        conn.commit()
        print(
            f"[DB] Alert logged: camera_id={camera_id}, type={alert_type}, "
            f"status={status}, risk={risk_level}"
        )
        return True
    except Error as e:
        conn.rollback()
        print(f"[DB] log_alert error: {e}")
        return False
    finally:
        safe_close(cursor, conn)


def save_setting(setting_key, setting_value):
    """Create or update one app setting."""
    conn = get_connection()
    if conn is None:
        print("[DB] save_setting skipped: DB unavailable")
        return False

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO app_settings (setting_key, setting_value)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE setting_value = VALUES(setting_value)
            """,
            (setting_key, str(setting_value)),
        )
        conn.commit()
        print(f"[DB] Setting saved: {setting_key}={setting_value}")
        return True
    except Error as e:
        conn.rollback()
        print(f"[DB] save_setting error: {e}")
        return False
    finally:
        safe_close(cursor, conn)


def get_setting(setting_key, default=None):
    """Get one setting by key, return default when missing."""
    conn = get_connection()
    if conn is None:
        print("[DB] get_setting skipped: DB unavailable")
        return default

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT setting_value FROM app_settings WHERE setting_key = %s LIMIT 1",
            (setting_key,),
        )
        row = cursor.fetchone()
        if not row:
            return default
        return row[0]
    except Error as e:
        print(f"[DB] get_setting error: {e}")
        return default
    finally:
        safe_close(cursor, conn)
