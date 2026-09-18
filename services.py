from db import get_db_connection


def get_event_stats(database_path, event_id):
    """
    Return an event together with organizer and attendance stats.
    """

    conn = get_db_connection(database_path)

    event = conn.execute(
        """
        SELECT
            e.*,
            u.name AS organizer_name,

            SUM(
                CASE
                    WHEN r.status = 'going'
                    THEN 1
                    ELSE 0
                END
            ) AS going_count,

            SUM(
                CASE
                    WHEN r.status = 'waitlist'
                    THEN 1
                    ELSE 0
                END
            ) AS waitlist_count,

            SUM(
                CASE
                    WHEN r.status = 'going'
                    AND r.checked_in = 1
                    THEN 1
                    ELSE 0
                END
            ) AS checked_in_count

        FROM events e

        JOIN users u
            ON e.owner_id = u.id

        LEFT JOIN rsvps r
            ON e.id = r.event_id

        WHERE e.id = ?

        GROUP BY e.id
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    if event:
        event = dict(event)

        event["going_count"] = (
            event["going_count"] or 0
        )

        event["waitlist_count"] = (
            event["waitlist_count"] or 0
        )

        event["checked_in_count"] = (
            event["checked_in_count"] or 0
        )

    return event


def promote_waitlist(database_path, event_id):
    """
    Promote the earliest waitlisted attendee if a confirmed
    attendee cancels and a spot becomes available.
    """

    conn = get_db_connection(database_path)

    event = conn.execute(
        """
        SELECT max_guests
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()

    if not event:
        conn.close()
        return

    going_count = conn.execute(
        """
        SELECT COUNT(*)
        FROM rsvps
        WHERE event_id = ?
        AND status = 'going'
        """,
        (event_id,),
    ).fetchone()[0]

    if going_count < event["max_guests"]:

        next_person = conn.execute(
            """
            SELECT id
            FROM rsvps
            WHERE event_id = ?
            AND status = 'waitlist'
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (event_id,),
        ).fetchone()

        if next_person:

            conn.execute(
                """
                UPDATE rsvps
                SET status = 'going'
                WHERE id = ?
                """,
                (next_person["id"],),
            )

            conn.commit()

    conn.close()


def get_user_event_lists(database_path, user_id):
    """
    Return the events a user created, joined, and saved.
    """

    conn = get_db_connection(database_path)

    created = [
        dict(row)
        for row in conn.execute(
            """
            SELECT
                e.*,

                SUM(
                    CASE
                        WHEN r.status = 'going'
                        THEN 1
                        ELSE 0
                    END
                ) AS going_count,

                SUM(
                    CASE
                        WHEN r.status = 'waitlist'
                        THEN 1
                        ELSE 0
                    END
                ) AS waitlist_count,

                SUM(
                    CASE
                        WHEN r.status = 'going'
                        AND r.checked_in = 1
                        THEN 1
                        ELSE 0
                    END
                ) AS checked_in_count

            FROM events e

            LEFT JOIN rsvps r
                ON e.id = r.event_id

            WHERE e.owner_id = ?

            GROUP BY e.id

            ORDER BY
                e.event_date,
                e.event_time
            """,
            (user_id,),
        ).fetchall()
    ]

    joined = [
        dict(row)
        for row in conn.execute(
            """
            SELECT
                e.*,
                u.name AS organizer_name,
                r.status AS rsvp_status

            FROM rsvps r

            JOIN events e
                ON r.event_id = e.id

            JOIN users u
                ON e.owner_id = u.id

            WHERE r.user_id = ?

            ORDER BY
                e.event_date,
                e.event_time
            """,
            (user_id,),
        ).fetchall()
    ]

    favorites = [
        dict(row)
        for row in conn.execute(
            """
            SELECT
                e.*,
                u.name AS organizer_name

            FROM favorites f

            JOIN events e
                ON f.event_id = e.id

            JOIN users u
                ON e.owner_id = u.id

            WHERE f.user_id = ?

            ORDER BY
                e.event_date,
                e.event_time
            """,
            (user_id,),
        ).fetchall()
    ]

    conn.close()

    for event in created:
        event["going_count"] = (
            event["going_count"] or 0
        )

        event["waitlist_count"] = (
            event["waitlist_count"] or 0
        )

        event["checked_in_count"] = (
            event["checked_in_count"] or 0
        )

    return created, joined, favorites