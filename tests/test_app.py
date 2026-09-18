import os
import sys
import tempfile
from pathlib import Path

import pytest


# ============================================================
# PROJECT IMPORT SETUP
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


import app as event_app


# ============================================================
# TEST FIXTURE
# ============================================================

@pytest.fixture()
def client():
    """
    Create a fresh temporary SQLite database for every test.

    This keeps automated tests completely separate from
    the real event_planner.db database.
    """

    db_fd, db_path = tempfile.mkstemp()

    event_app.DB_NAME = db_path

    event_app.app.config["TESTING"] = True
    event_app.app.config["SECRET_KEY"] = "test-secret"

    event_app.init_db()
    event_app.migrate_db()

    with event_app.app.test_client() as test_client:
        yield test_client

    os.close(db_fd)

    if os.path.exists(db_path):
        os.unlink(db_path)


# ============================================================
# TEST HELPERS
# ============================================================

def register_user(
    client,
    name="Test User",
    email="tester@example.com",
    password="test123",
):
    return client.post(
        "/register",
        data={
            "name": name,
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )


def login_user(
    client,
    email="tester@example.com",
    password="test123",
):
    return client.post(
        "/login",
        data={
            "email": email,
            "password": password,
        },
        follow_redirects=True,
    )


def logout_user(client):
    return client.get(
        "/logout",
        follow_redirects=True,
    )


def create_test_event(
    client,
    title="AI Community Meetup",
    max_guests="5",
):
    return client.post(
        "/events/create",
        data={
            "title": title,
            "category": "Technology",
            "event_date": "2030-12-01",
            "event_time": "18:00",
            "location": "Rutgers University",
            "max_guests": max_guests,
            "image_url": "",
            "description": (
                "A test event for Event Planner "
                "automated testing."
            ),
        },
        follow_redirects=True,
    )


def get_event_id_by_title(title):
    conn = event_app.get_db()

    event = conn.execute(
        """
        SELECT id
        FROM events
        WHERE title = ?
        """,
        (title,),
    ).fetchone()

    conn.close()

    return event["id"] if event else None


# ============================================================
# HOMEPAGE
# ============================================================

def test_homepage_loads(client):
    response = client.get("/")

    assert response.status_code == 200
    assert b"Event Planner" in response.data


# ============================================================
# REGISTRATION
# ============================================================

def test_register_user(client):
    response = register_user(client)

    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_duplicate_registration_is_rejected(client):
    register_user(client)

    logout_user(client)

    response = register_user(client)

    assert response.status_code == 200
    assert b"already exists" in response.data


def test_short_password_registration_is_rejected(client):
    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "tester@example.com",
            "password": "123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"at least 6 characters" in response.data


# ============================================================
# LOGIN
# ============================================================

def test_login_user(client):
    register_user(client)

    logout_user(client)

    response = login_user(client)

    assert response.status_code == 200
    assert b"Dashboard" in response.data


def test_login_with_wrong_password(client):
    register_user(client)

    logout_user(client)

    response = login_user(
        client,
        password="wrongpassword",
    )

    assert response.status_code == 200
    assert b"Incorrect email or password" in response.data


# ============================================================
# AUTHORIZATION
# ============================================================

def test_dashboard_requires_login(client):
    response = client.get(
        "/dashboard",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please log in to continue" in response.data


def test_create_event_requires_login(client):
    response = client.get(
        "/events/create",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Please log in to continue" in response.data


# ============================================================
# EVENT CREATION
# ============================================================

def test_create_event(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    response = create_test_event(
        client,
        title="AI Networking Night",
        max_guests="50",
    )

    assert response.status_code == 200
    assert b"AI Networking Night" in response.data
    assert b"Event created successfully" in response.data


def test_created_event_appears_on_homepage(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Machine Learning Meetup",
        max_guests="80",
    )

    response = client.get("/")

    assert response.status_code == 200
    assert b"Machine Learning Meetup" in response.data


def test_event_is_stored_in_database(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Stored Event Test",
        max_guests="25",
    )

    conn = event_app.get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE title = ?
        """,
        ("Stored Event Test",),
    ).fetchone()

    conn.close()

    assert event is not None
    assert event["max_guests"] == 25
    assert event["status"] == "upcoming"


# ============================================================
# RSVP
# ============================================================

def test_user_can_rsvp_to_event(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="RSVP Test Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "RSVP Test Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"RSVP confirmed" in response.data


def test_duplicate_rsvp_is_rejected(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Duplicate RSVP Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Duplicate RSVP Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"already have an RSVP" in response.data


def test_organizer_cannot_rsvp_to_own_event(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Owner RSVP Test",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Owner RSVP Test"
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You are the organizer" in response.data


# ============================================================
# WAITLIST
# ============================================================

def test_second_guest_is_waitlisted_when_event_is_full(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Waitlist Test Event",
        max_guests="1",
    )

    event_id = get_event_id_by_title(
        "Waitlist Test Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest One",
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    logout_user(client)

    register_user(
        client,
        name="Guest Two",
        email="guest2@example.com",
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"added to the waitlist" in response.data


def test_waitlisted_guest_status_is_saved(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Waitlist Database Test",
        max_guests="1",
    )

    event_id = get_event_id_by_title(
        "Waitlist Database Test"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest One",
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    logout_user(client)

    register_user(
        client,
        name="Guest Two",
        email="guest2@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    conn = event_app.get_db()

    guest_two = conn.execute(
        """
        SELECT r.status
        FROM rsvps r

        JOIN users u
            ON r.user_id = u.id

        WHERE r.event_id = ?
        AND u.email = ?
        """,
        (
            event_id,
            "guest2@example.com",
        ),
    ).fetchone()

    conn.close()

    assert guest_two is not None
    assert guest_two["status"] == "waitlist"


def test_waitlisted_guest_is_promoted_after_cancellation(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Promotion Test Event",
        max_guests="1",
    )

    event_id = get_event_id_by_title(
        "Promotion Test Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest One",
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    logout_user(client)

    register_user(
        client,
        name="Guest Two",
        email="guest2@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    logout_user(client)

    login_user(
        client,
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/cancel-rsvp",
        follow_redirects=True,
    )

    conn = event_app.get_db()

    promoted_user = conn.execute(
        """
        SELECT r.status
        FROM rsvps r

        JOIN users u
            ON r.user_id = u.id

        WHERE r.event_id = ?
        AND u.email = ?
        """,
        (
            event_id,
            "guest2@example.com",
        ),
    ).fetchone()

    conn.close()

    assert promoted_user is not None
    assert promoted_user["status"] == "going"


# ============================================================
# CANCEL RSVP
# ============================================================

def test_user_can_cancel_rsvp(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Cancel RSVP Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Cancel RSVP Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    response = client.post(
        f"/events/{event_id}/cancel-rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"RSVP has been cancelled" in response.data

    conn = event_app.get_db()

    remaining_rsvp = conn.execute(
        """
        SELECT id
        FROM rsvps
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    assert remaining_rsvp is None


# ============================================================
# CANCELLED EVENTS
# ============================================================

def test_cancelled_event_rejects_rsvp(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Cancelled Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Cancelled Event"
    )

    conn = event_app.get_db()

    conn.execute(
        """
        UPDATE events
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (event_id,),
    )

    conn.commit()
    conn.close()

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"event has been cancelled" in response.data


def test_cancelled_event_is_hidden_from_homepage(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Hidden Cancelled Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Hidden Cancelled Event"
    )

    conn = event_app.get_db()

    conn.execute(
        """
        UPDATE events
        SET status = 'cancelled'
        WHERE id = ?
        """,
        (event_id,),
    )

    conn.commit()
    conn.close()

    response = client.get("/")

    assert response.status_code == 200
    assert b"Hidden Cancelled Event" not in response.data


# ============================================================
# FAVORITES
# ============================================================

def test_user_can_save_event(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Favorite Test Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Favorite Test Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    response = client.post(
        f"/events/{event_id}/favorite",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Event saved" in response.data


def test_user_can_remove_saved_event(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Remove Favorite Event",
        max_guests="5",
    )

    event_id = get_event_id_by_title(
        "Remove Favorite Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/favorite",
        follow_redirects=True,
    )

    response = client.post(
        f"/events/{event_id}/favorite",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Removed from saved events" in response.data


# ============================================================
# ANALYTICS PERMISSIONS
# ============================================================

def test_organizer_can_open_analytics(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Analytics Test Event",
        max_guests="10",
    )

    event_id = get_event_id_by_title(
        "Analytics Test Event"
    )

    response = client.get(
        f"/events/{event_id}/analytics"
    )

    assert response.status_code == 200
    assert b"Analytics" in response.data


def test_non_owner_cannot_open_analytics(client):
    register_user(
        client,
        name="Organizer",
        email="organizer@example.com",
    )

    create_test_event(
        client,
        title="Private Analytics Event",
        max_guests="10",
    )

    event_id = get_event_id_by_title(
        "Private Analytics Event"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest User",
        email="guest@example.com",
    )

    response = client.get(
        f"/events/{event_id}/analytics"
    )

    assert response.status_code == 403


# ============================================================
# 404
# ============================================================

def test_404_page(client):
    response = client.get(
        "/events/999999"
    )

    assert response.status_code == 404
    assert b"Page not found" in response.data