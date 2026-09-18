import sqlite3


def get_db_connection(database_path):
    """
    Open a SQLite database connection.

    Rows are returned like dictionaries so we can access
    columns using names such as row["title"].
    """

    conn = sqlite3.connect(database_path)

    conn.row_factory = sqlite3.Row

    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    return conn


def init_db(database_path):
    """
    Create all required database tables if they do not exist.
    """

    conn = get_db_connection(
        database_path
    )

    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            event_date TEXT NOT NULL,
            event_time TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT,
            max_guests INTEGER NOT NULL,
            image_url TEXT,
            status TEXT NOT NULL DEFAULT 'upcoming',
            is_featured INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,

            FOREIGN KEY(owner_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'going',
            checked_in INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,

            UNIQUE(event_id, user_id),

            FOREIGN KEY(event_id)
                REFERENCES events(id)
                ON DELETE CASCADE,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,

            UNIQUE(event_id, user_id),

            FOREIGN KEY(event_id)
                REFERENCES events(id)
                ON DELETE CASCADE,

            FOREIGN KEY(user_id)
                REFERENCES users(id)
                ON DELETE CASCADE
        );
        """
    )

    conn.commit()
    conn.close()


def migrate_db(database_path):
    """
    Upgrade older databases without deleting existing data.
    """

    conn = get_db_connection(
        database_path
    )

    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(events)"
        ).fetchall()
    }

    if "image_url" not in columns:
        conn.execute(
            """
            ALTER TABLE events
            ADD COLUMN image_url TEXT
            """
        )

    if "status" not in columns:
        conn.execute(
            """
            ALTER TABLE events
            ADD COLUMN status TEXT
            NOT NULL DEFAULT 'upcoming'
            """
        )

    if "is_featured" not in columns:
        conn.execute(
            """
            ALTER TABLE events
            ADD COLUMN is_featured INTEGER
            NOT NULL DEFAULT 0
            """
        )

    conn.commit()
    conn.close()