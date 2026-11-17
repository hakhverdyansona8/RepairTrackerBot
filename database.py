import sqlite3
import json
import os

from contextlib import contextmanager


DB_NAME = "repairs.db"
JSON_FILE = "repairs.json"

VALID_STATUSES = {
    "Pending",
    "In Progress",
    "Completed"
}

ALLOWED_FIELDS = {
    "customer_name",
    "device",
    "problem",
    "price",
    "status"
}


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.execute("PRAGMA busy_timeout = 5000")

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def validate_text(value, field_name):
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be text")

    value = value.strip()

    if not value:
        raise ValueError(f"{field_name} cannot be empty")

    return value


def validate_price(price):
    if isinstance(price, bool):
        raise ValueError("Price must be a positive integer")

    if isinstance(price, int):
        value = price
    elif isinstance(price, str) and price.strip().isdigit():
        value = int(price.strip())
    else:
        raise ValueError("Price must be a positive integer")

    if value <= 0:
        raise ValueError("Price must be greater than zero")

    return value


def validate_status(status):
    if not isinstance(status, str):
        raise ValueError("Invalid repair status")

    status = status.strip()

    if status not in VALID_STATUSES:
        raise ValueError("Invalid repair status")

    return status


def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS repairs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                device TEXT NOT NULL,
                problem TEXT NOT NULL,
                price INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pending',
                owner_id INTEGER
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("PRAGMA table_info(repairs)")
        columns = [column[1] for column in cursor.fetchall()]

        if "owner_id" not in columns:
            cursor.execute("""
                ALTER TABLE repairs
                ADD COLUMN owner_id INTEGER
            """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repairs_owner_id
            ON repairs(owner_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repairs_status
            ON repairs(status)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_repairs_owner_status
            ON repairs(owner_id, status)
        """)

    print("Database initialized successfully!")


def register_user(
    user_id,
    username=None,
    first_name=None,
    last_name=None
):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO users (
                telegram_id,
                username,
                first_name,
                last_name
            )
            VALUES (?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name
        """, (user_id, username, first_name, last_name))


def assign_legacy_repairs(admin_id):
    if not isinstance(admin_id, int) or isinstance(admin_id, bool) or admin_id <= 0:
        raise ValueError("Invalid Admin ID")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE repairs
            SET owner_id = ?
            WHERE owner_id IS NULL
        """, (admin_id,))

    print("Legacy repairs assigned successfully!")


def migrate_json():
    if not os.path.exists(JSON_FILE):
        print("No JSON file found. Migration skipped.")
        return

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM repairs")
        count = cursor.fetchone()[0]

        if count > 0:
            print("Database already contains data. Migration skipped.")
            return

        try:
            with open(JSON_FILE, "r", encoding="utf-8") as file:
                data = json.load(file)

        except (json.JSONDecodeError, OSError) as error:
            raise ValueError(
                f"Could not read {JSON_FILE}: {error}"
            ) from error

        if not isinstance(data, list):
            raise ValueError("JSON data must contain a list of repairs")

        for repair in data:
            if not isinstance(repair, dict):
                raise ValueError("Invalid repair record in JSON file")

            customer_name = validate_text(
                repair.get("customer_name"),
                "Customer name"
            )

            device = validate_text(
                repair.get("device"),
                "Device"
            )

            problem = validate_text(
                repair.get("problem"),
                "Problem"
            )

            price = validate_price(repair.get("price"))

            status = repair.get("status", "Pending")

            if status is None or status == "":
                status = "Pending"
            else:
                status = validate_status(status)

            cursor.execute("""
                INSERT INTO repairs (
                    customer_name,
                    device,
                    problem,
                    price,
                    status
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                customer_name,
                device,
                problem,
                price,
                status
            ))

    print(f"Successfully migrated {len(data)} repairs!")


def add_repair(customer_name, device, problem, price, user_id):
    customer_name = validate_text(customer_name, "Customer name")
    device = validate_text(device, "Device")
    problem = validate_text(problem, "Problem")
    price = validate_price(price)

    if not isinstance(user_id, int) or isinstance(user_id, bool) or user_id <= 0:
        raise ValueError("Invalid user ID")

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO repairs (
                customer_name,
                device,
                problem,
                price,
                owner_id
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            customer_name,
            device,
            problem,
            price,
            user_id
        ))

        repair_id = cursor.lastrowid

    return repair_id


def get_all_repairs(user_id):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM repairs
            WHERE owner_id = ?
            ORDER BY id ASC
        """, (user_id,))

        return cursor.fetchall()


def get_repair_by_id(repair_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM repairs
            WHERE id = ? AND owner_id = ?
        """, (repair_id, user_id))

        return cursor.fetchone()


def update_repair(repair_id, field, new_value, user_id):
    if field not in ALLOWED_FIELDS:
        raise ValueError("Invalid field")

    if field in {"customer_name", "device", "problem"}:
        new_value = validate_text(new_value, field)

    elif field == "price":
        new_value = validate_price(new_value)

    elif field == "status":
        new_value = validate_status(new_value)

    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute(
            f"""
            UPDATE repairs
            SET {field} = ?
            WHERE id = ? AND owner_id = ?
            """,
            (new_value, repair_id, user_id)
        )

        return cursor.rowcount > 0


def delete_repair(repair_id, user_id):
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            DELETE FROM repairs
            WHERE id = ? AND owner_id = ?
        """, (repair_id, user_id))

        return cursor.rowcount > 0


def get_all_users():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                users.telegram_id,
                users.username,
                users.first_name,
                users.last_name,
                users.created_at,
                COUNT(repairs.id) AS repair_count
            FROM users
            LEFT JOIN repairs
                ON users.telegram_id = repairs.owner_id
            GROUP BY users.telegram_id
            ORDER BY users.created_at DESC
        """)

        return cursor.fetchall()


def get_admin_statistics():
    with get_connection() as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM repairs")
        total_repairs = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM repairs
            WHERE status = 'Pending'
        """)
        pending = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM repairs
            WHERE status = 'In Progress'
        """)
        in_progress = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COUNT(*) FROM repairs
            WHERE status = 'Completed'
        """)
        completed = cursor.fetchone()[0]

        cursor.execute("""
            SELECT COALESCE(SUM(price), 0)
            FROM repairs
        """)
        total_revenue = cursor.fetchone()[0]

        return {
            "total_users": total_users,
            "total_repairs": total_repairs,
            "pending": pending,
            "in_progress": in_progress,
            "completed": completed,
            "total_revenue": total_revenue
        }


if __name__ == "__main__":
    init_db()
    migrate_json()
    print("Database is ready!")
