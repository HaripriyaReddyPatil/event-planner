from datetime import datetime


def now_iso():
    """
    Return the current timestamp in ISO format.

    Example:
    2026-09-18T14:35:20
    """

    return datetime.now().isoformat(
        timespec="seconds"
    )


def is_past(event_date, event_time):
    """
    Return True if the supplied event date and time
    are earlier than the current local time.
    """

    try:
        event_datetime = datetime.strptime(
            f"{event_date} {event_time}",
            "%Y-%m-%d %H:%M",
        )

        return event_datetime < datetime.now()

    except ValueError:
        return False


def calculate_percentage(value, total):
    """
    Safely calculate a percentage.

    Returns 0 if the total is zero or invalid.
    """

    if not total or total <= 0:
        return 0

    return round(
        (value / total) * 100
    )


def clamp_percentage(value):
    """
    Keep a percentage between 0 and 100.
    """

    return max(
        0,
        min(
            100,
            value,
        ),
    )