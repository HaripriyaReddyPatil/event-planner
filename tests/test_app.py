import os
import sys
import tempfile


# ============================================================
# MAKE PROJECT ROOT IMPORTABLE
# ============================================================

PROJECT_ROOT = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT,
    )


import pytest

import app as event_app


# ============================================================
# TEST FIXTURE
# ============================================================

@pytest.fixture
def client():

    db_fd, db_path = tempfile.mkstemp()

    original_db_name = event_app.DB_NAME

    event_app.DB_NAME = db_path

    event_app.app.config["TESTING"] = True
    event_app.app.config["SECRET_KEY"] = "test-secret"

    event_app.init_db()
    event_app.migrate_db()

    with event_app.app.test_client() as client:
        yield client

    event_app.DB_NAME = original_db_name

    os.close(db_fd)

    if os.path.exists(db_path):
        os.unlink(db_path)


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def register_user(
    client,
    name="Test User",
    email="test@example.com",
    password="password123",
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
    email="test@example.com",
    password="password123",
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
    title="Python Workshop",
    category="Technology",
    event_date="2099-12-20",
    event_time="18:00",
    location="Rutgers University",
    description="Learn Python with practical examples.",
    max_guests="10",
    image_url="",
):

    return client.post(
        "/events/create",
        data={
            "title": title,
            "category": category,
            "event_date": event_date,
            "event_time": event_time,
            "location": location,
            "description": description,
            "max_guests": max_guests,
            "image_url": image_url,
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

    assert event is not None

    return event["id"]


def create_owner_and_event(
    client,
    title="Python Workshop",
    max_guests="10",
):

    register_user(
        client,
        name="Organizer",
        email="owner@example.com",
        password="password123",
    )

    create_test_event(
        client,
        title=title,
        max_guests=max_guests,
    )

    return get_event_id_by_title(
        title
    )


# ============================================================
# BASIC PAGE TESTS
# ============================================================

def test_homepage_loads(client):

    response = client.get("/")

    assert response.status_code == 200


def test_404_page(client):

    response = client.get(
        "/this-page-does-not-exist"
    )

    assert response.status_code == 404


# ============================================================
# REGISTRATION TESTS
# ============================================================

def test_register_user(client):

    response = register_user(client)

    assert response.status_code == 200

    conn = event_app.get_db()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE email = ?
        """,
        ("test@example.com",),
    ).fetchone()

    conn.close()

    assert user is not None
    assert user["name"] == "Test User"


def test_duplicate_registration(client):

    register_user(client)

    logout_user(client)

    response = register_user(client)

    assert response.status_code == 200

    assert (
        b"already exists"
        in response.data
    )


def test_short_password_rejected(client):

    response = client.post(
        "/register",
        data={
            "name": "Test User",
            "email": "short@example.com",
            "password": "123",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"at least 6 characters"
        in response.data
    )


# ============================================================
# LOGIN TESTS
# ============================================================

def test_login_user(client):

    register_user(client)

    logout_user(client)

    response = login_user(client)

    assert response.status_code == 200

    assert (
        b"Dashboard"
        in response.data
    )


def test_wrong_password(client):

    register_user(client)

    logout_user(client)

    response = login_user(
        client,
        password="wrong-password",
    )

    assert response.status_code == 200

    assert (
        b"Incorrect email or password"
        in response.data
    )


def test_dashboard_requires_login(client):

    response = client.get(
        "/dashboard",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"Please log in"
        in response.data
    )


# ============================================================
# EVENT CREATION TESTS
# ============================================================

def test_create_page_requires_login(client):

    response = client.get(
        "/events/create",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"Please log in"
        in response.data
    )


def test_create_event(client):

    register_user(client)

    response = create_test_event(client)

    assert response.status_code == 200

    assert (
        b"Python Workshop"
        in response.data
    )


def test_event_appears_on_homepage(client):

    register_user(client)

    create_test_event(client)

    response = client.get("/")

    assert response.status_code == 200

    assert (
        b"Python Workshop"
        in response.data
    )


def test_event_stored_in_database(client):

    register_user(client)

    create_test_event(client)

    conn = event_app.get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE title = ?
        """,
        ("Python Workshop",),
    ).fetchone()

    conn.close()

    assert event is not None
    assert event["category"] == "Technology"
    assert event["max_guests"] == 10


# ============================================================
# RSVP TESTS
# ============================================================

def test_rsvp_to_event(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
        email="guest@example.com",
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"RSVP confirmed"
        in response.data
    )


def test_duplicate_rsvp(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
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

    assert (
        b"already have an RSVP"
        in response.data
    )


def test_owner_cannot_rsvp(client):

    event_id = create_owner_and_event(
        client
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert response.status_code == 200

    assert (
        b"organizer of this event"
        in response.data
    )


def test_second_guest_is_waitlisted(client):

    event_id = create_owner_and_event(
        client,
        max_guests="1",
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

    assert (
        b"waitlist"
        in response.data.lower()
    )


def test_waitlist_status_in_database(client):

    event_id = create_owner_and_event(
        client,
        max_guests="1",
    )

    logout_user(client)

    register_user(
        client,
        name="Guest One",
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest Two",
        email="guest2@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    conn = event_app.get_db()

    guest = conn.execute(
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

    assert guest is not None
    assert guest["status"] == "waitlist"


def test_waitlist_promotion_after_cancellation(client):

    event_id = create_owner_and_event(
        client,
        max_guests="1",
    )

    logout_user(client)

    register_user(
        client,
        name="Guest One",
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    logout_user(client)

    register_user(
        client,
        name="Guest Two",
        email="guest2@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    logout_user(client)

    login_user(
        client,
        email="guest1@example.com",
    )

    client.post(
        f"/events/{event_id}/cancel-rsvp"
    )

    conn = event_app.get_db()

    promoted = conn.execute(
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

    assert promoted is not None
    assert promoted["status"] == "going"


def test_user_can_cancel_rsvp(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    client.post(
        f"/events/{event_id}/cancel-rsvp"
    )

    conn = event_app.get_db()

    rsvp = conn.execute(
        """
        SELECT *
        FROM rsvps
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    assert rsvp is None


def test_cancelled_event_rejects_rsvp(client):

    event_id = create_owner_and_event(
        client
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
        name="Guest",
        email="guest@example.com",
    )

    response = client.post(
        f"/events/{event_id}/rsvp",
        follow_redirects=True,
    )

    assert (
        b"cancelled"
        in response.data.lower()
    )


def test_cancelled_event_hidden_from_homepage(client):

    event_id = create_owner_and_event(
        client
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

    assert (
        b"Python Workshop"
        not in response.data
    )


# ============================================================
# FAVORITE TESTS
# ============================================================

def test_save_event(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/favorite"
    )

    conn = event_app.get_db()

    favorite = conn.execute(
        """
        SELECT *
        FROM favorites
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    assert favorite is not None


def test_remove_favorite(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/favorite"
    )

    client.post(
        f"/events/{event_id}/favorite"
    )

    conn = event_app.get_db()

    favorite = conn.execute(
        """
        SELECT *
        FROM favorites
        WHERE event_id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    assert favorite is None


# ============================================================
# ANALYTICS TESTS
# ============================================================

def test_organizer_can_view_analytics(client):

    event_id = create_owner_and_event(
        client
    )

    response = client.get(
        f"/events/{event_id}/analytics"
    )

    assert response.status_code == 200


def test_non_owner_cannot_view_analytics(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
        email="guest@example.com",
    )

    response = client.get(
        f"/events/{event_id}/analytics"
    )

    assert response.status_code == 403


# ============================================================
# NEW: EVENT EDITING TESTS
# ============================================================

def test_owner_can_edit_event(client):

    event_id = create_owner_and_event(
        client
    )

    response = client.post(
        f"/events/{event_id}/edit",
        data={
            "title": "Advanced Python Workshop",
            "category": "Technology",
            "event_date": "2099-12-21",
            "event_time": "19:00",
            "location": "Busch Campus",
            "description": "Updated event description.",
            "max_guests": "25",
            "image_url": "",
            "status": "upcoming",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = event_app.get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    assert (
        event["title"]
        == "Advanced Python Workshop"
    )

    assert (
        event["location"]
        == "Busch Campus"
    )

    assert event["max_guests"] == 25


def test_non_owner_cannot_edit_event(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Other User",
        email="other@example.com",
    )

    response = client.get(
        f"/events/{event_id}/edit"
    )

    assert response.status_code == 403


# ============================================================
# NEW: CLONE TEST
# ============================================================

def test_owner_can_duplicate_event(client):

    event_id = create_owner_and_event(
        client
    )

    response = client.post(
        f"/events/{event_id}/clone",
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = event_app.get_db()

    copied = conn.execute(
        """
        SELECT *
        FROM events
        WHERE title = ?
        """,
        ("Python Workshop (Copy)",),
    ).fetchone()

    conn.close()

    assert copied is not None
    assert copied["status"] == "upcoming"


# ============================================================
# NEW: DELETE TEST
# ============================================================

def test_owner_can_delete_event(client):

    event_id = create_owner_and_event(
        client
    )

    response = client.post(
        f"/events/{event_id}/delete",
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = event_app.get_db()

    event = conn.execute(
        """
        SELECT *
        FROM events
        WHERE id = ?
        """,
        (event_id,),
    ).fetchone()

    conn.close()

    assert event is None


# ============================================================
# NEW: CHECK-IN TEST
# ============================================================

def test_organizer_can_check_in_attendee(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Guest",
        email="guest@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    conn = event_app.get_db()

    guest = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        ("guest@example.com",),
    ).fetchone()

    conn.close()

    guest_id = guest["id"]

    logout_user(client)

    login_user(
        client,
        email="owner@example.com",
    )

    response = client.post(
        f"/events/{event_id}/check-in/{guest_id}",
        follow_redirects=True,
    )

    assert response.status_code == 200

    conn = event_app.get_db()

    rsvp = conn.execute(
        """
        SELECT checked_in
        FROM rsvps
        WHERE event_id = ?
        AND user_id = ?
        """,
        (
            event_id,
            guest_id,
        ),
    ).fetchone()

    conn.close()

    assert rsvp["checked_in"] == 1


# ============================================================
# NEW: CSV EXPORT TEST
# ============================================================

def test_csv_attendee_export(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="CSV Guest",
        email="csvguest@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    logout_user(client)

    login_user(
        client,
        email="owner@example.com",
    )

    response = client.get(
        f"/events/{event_id}/export"
    )

    assert response.status_code == 200

    assert (
        "text/csv"
        in response.content_type
    )

    assert (
        b"CSV Guest"
        in response.data
    )

    assert (
        b"csvguest@example.com"
        in response.data
    )


# ============================================================
# NEW: CALENDAR EXPORT TEST
# ============================================================

def test_calendar_export(client):

    event_id = create_owner_and_event(
        client
    )

    response = client.get(
        f"/events/{event_id}/calendar"
    )

    assert response.status_code == 200

    assert (
        "text/calendar"
        in response.content_type
    )

    assert (
        b"BEGIN:VCALENDAR"
        in response.data
    )

    assert (
        b"Python Workshop"
        in response.data
    )


# ============================================================
# NEW: DASHBOARD RSVP STATUS TEST
# ============================================================

def test_dashboard_displays_going_rsvp_status(client):

    event_id = create_owner_and_event(
        client
    )

    logout_user(client)

    register_user(
        client,
        name="Dashboard Guest",
        email="dashboard@example.com",
    )

    client.post(
        f"/events/{event_id}/rsvp"
    )

    response = client.get(
        "/dashboard"
    )

    assert response.status_code == 200

    assert (
        b"Python Workshop"
        in response.data
    )

    assert (
        b"Going"
        in response.data
    )