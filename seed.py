import random

from werkzeug.security import generate_password_hash

from db import get_db_connection, init_db, migrate_db
from config import Config
from helpers import now_iso


DB_PATH = Config.DATABASE


DEMO_USERS = [
    {
        "name": "Aarav Mehta",
        "email": "aarav.demo@example.com",
    },
    {
        "name": "Maya Shah",
        "email": "maya.demo@example.com",
    },
    {
        "name": "Noah Williams",
        "email": "noah.demo@example.com",
    },
    {
        "name": "Sophia Chen",
        "email": "sophia.demo@example.com",
    },
    {
        "name": "Ethan Brooks",
        "email": "ethan.demo@example.com",
    },
    {
        "name": "Olivia Martin",
        "email": "olivia.demo@example.com",
    },
    {
        "name": "Rohan Patel",
        "email": "rohan.demo@example.com",
    },
    {
        "name": "Emma Davis",
        "email": "emma.demo@example.com",
    },
]


DEMO_EVENTS = [
    {
        "title": "AI & Machine Learning Meetup",
        "category": "Technology",
        "event_date": "2026-10-03",
        "event_time": "18:30",
        "location": "Busch Student Center, Piscataway",
        "description": (
            "An evening meetup for students interested in AI, "
            "machine learning, LLMs, and applied data science."
        ),
        "max_guests": 40,
        "image_url": (
            "https://images.unsplash.com/photo-1485827404703-89b55fcc595e"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Resume & LinkedIn Workshop",
        "category": "Career",
        "event_date": "2026-10-05",
        "event_time": "16:00",
        "location": "Livingston Student Center",
        "description": (
            "A hands-on session focused on improving resumes, "
            "LinkedIn profiles, and technical job applications."
        ),
        "max_guests": 30,
        "image_url": (
            "https://images.unsplash.com/photo-1521737711867-e3b97375f902"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Python Coding Night",
        "category": "Technology",
        "event_date": "2026-10-08",
        "event_time": "19:00",
        "location": "Hill Center, Busch Campus",
        "description": (
            "A collaborative coding session for practicing Python, "
            "algorithms, APIs, and small projects."
        ),
        "max_guests": 25,
        "image_url": (
            "https://images.unsplash.com/photo-1515879218367-8466d910aaa4"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Graduate Student Coffee Social",
        "category": "Social",
        "event_date": "2026-10-10",
        "event_time": "15:00",
        "location": "College Avenue Student Center",
        "description": (
            "A casual social event for graduate students to meet, "
            "network, and make new friends."
        ),
        "max_guests": 50,
        "image_url": (
            "https://images.unsplash.com/photo-1495474472287-4d71bcdd2085"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Data Science Research Talk",
        "category": "Academic",
        "event_date": "2026-10-12",
        "event_time": "17:30",
        "location": "CoRE Building, Busch Campus",
        "description": (
            "A research talk covering data-driven methods, "
            "experimentation, and real-world analytics."
        ),
        "max_guests": 35,
        "image_url": (
            "https://images.unsplash.com/photo-1551288049-bebda4e38f71"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Women in Tech Networking Evening",
        "category": "Career",
        "event_date": "2026-10-15",
        "event_time": "18:00",
        "location": "Rutgers Business School, Livingston",
        "description": (
            "Networking, career discussions, and mentorship "
            "for students interested in technology careers."
        ),
        "max_guests": 45,
        "image_url": (
            "https://images.unsplash.com/photo-1517245386807-bb43f82c33c4"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Hackathon Team Mixer",
        "category": "Technology",
        "event_date": "2026-10-18",
        "event_time": "14:00",
        "location": "Richard Weeks Hall, Busch Campus",
        "description": (
            "Meet developers, designers, and data students "
            "looking to form hackathon teams."
        ),
        "max_guests": 60,
        "image_url": (
            "https://images.unsplash.com/photo-1504384308090-c894fdcc538d"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Campus Photography Walk",
        "category": "Arts",
        "event_date": "2026-10-20",
        "event_time": "16:30",
        "location": "Voorhees Mall, College Avenue",
        "description": (
            "A relaxed photography walk across campus. "
            "Phones and cameras are both welcome."
        ),
        "max_guests": 20,
        "image_url": (
            "https://images.unsplash.com/photo-1452780212940-6f5c0d14d848"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Beginner Badminton Meetup",
        "category": "Sports",
        "event_date": "2026-10-22",
        "event_time": "18:00",
        "location": "Werblin Recreation Center",
        "description": (
            "A beginner-friendly badminton meetup for students "
            "looking to play casually and meet others."
        ),
        "max_guests": 24,
        "image_url": (
            "https://images.unsplash.com/photo-1626224583764-f87db24ac4ea"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Community Volunteer Day",
        "category": "Community",
        "event_date": "2026-10-24",
        "event_time": "09:30",
        "location": "New Brunswick Community Center",
        "description": (
            "A student volunteer event supporting local "
            "community organizations and outreach programs."
        ),
        "max_guests": 35,
        "image_url": (
            "https://images.unsplash.com/photo-1559027615-cd4628902d4a"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Cloud Computing Study Session",
        "category": "Academic",
        "event_date": "2026-10-27",
        "event_time": "17:00",
        "location": "Alexander Library",
        "description": (
            "A peer study session covering cloud concepts, "
            "distributed systems, and exam preparation."
        ),
        "max_guests": 18,
        "image_url": (
            "https://images.unsplash.com/photo-1451187580459-43490279c0fa"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Startup Pitch Practice",
        "category": "Career",
        "event_date": "2026-10-30",
        "event_time": "18:30",
        "location": "Rutgers Makerspace",
        "description": (
            "Students practice startup pitches and receive "
            "feedback on ideas, storytelling, and presentation."
        ),
        "max_guests": 25,
        "image_url": (
            "https://images.unsplash.com/photo-1556761175-b413da4baf72"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Fall Game Night",
        "category": "Social",
        "event_date": "2026-11-02",
        "event_time": "19:00",
        "location": "Busch Student Center",
        "description": (
            "Board games, card games, snacks, and a relaxed "
            "evening for students across different programs."
        ),
        "max_guests": 40,
        "image_url": (
            "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Intro to Generative AI",
        "category": "Technology",
        "event_date": "2026-11-05",
        "event_time": "18:00",
        "location": "CoRE Auditorium",
        "description": (
            "An introductory session on generative AI, "
            "LLMs, prompting, retrieval, and AI applications."
        ),
        "max_guests": 55,
        "image_url": (
            "https://images.unsplash.com/photo-1677442136019-21780ecad995"
            "?auto=format&fit=crop&w=1600&q=80"
        ),
        "status": "upcoming",
    },
    {
        "title": "Cancelled Demo Event",
        "category": "Other",
        "event_date": "2026-11-08",
        "event_time": "14:00",
        "location": "College Avenue Campus",
        "description": (
            "A cancelled event included to demonstrate "
            "event-status handling in the application."
        ),
        "max_guests": 20,
        "image_url": "",
        "status": "cancelled",
    },
]


def get_or_create_user(
    conn,
    name,
    email,
    password="demo123",
):
    existing = conn.execute(
        """
        SELECT id
        FROM users
        WHERE email = ?
        """,
        (email,),
    ).fetchone()

    if existing:
        return existing["id"]

    password_hash = generate_password_hash(
        password,
        method="pbkdf2:sha256",
    )

    cursor = conn.execute(
        """
        INSERT INTO users (
            name,
            email,
            password_hash,
            created_at
        )
        VALUES (?, ?, ?, ?)
        """,
        (
            name,
            email,
            password_hash,
            now_iso(),
        ),
    )

    return cursor.lastrowid


def get_or_create_event(
    conn,
    owner_id,
    event,
):
    existing = conn.execute(
        """
        SELECT id
        FROM events
        WHERE title = ?
        """,
        (event["title"],),
    ).fetchone()

    if existing:
        return existing["id"]

    cursor = conn.execute(
        """
        INSERT INTO events (
            owner_id,
            title,
            category,
            event_date,
            event_time,
            location,
            description,
            max_guests,
            image_url,
            status,
            is_featured,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            owner_id,
            event["title"],
            event["category"],
            event["event_date"],
            event["event_time"],
            event["location"],
            event["description"],
            event["max_guests"],
            event["image_url"] or None,
            event["status"],
            0,
            now_iso(),
        ),
    )

    return cursor.lastrowid


def add_rsvp(
    conn,
    event_id,
    user_id,
    status,
    checked_in=0,
):
    existing = conn.execute(
        """
        SELECT id
        FROM rsvps
        WHERE event_id = ?
        AND user_id = ?
        """,
        (
            event_id,
            user_id,
        ),
    ).fetchone()

    if existing:
        return

    conn.execute(
        """
        INSERT INTO rsvps (
            event_id,
            user_id,
            status,
            checked_in,
            created_at
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            event_id,
            user_id,
            status,
            checked_in,
            now_iso(),
        ),
    )


def add_favorite(
    conn,
    event_id,
    user_id,
):
    existing = conn.execute(
        """
        SELECT id
        FROM favorites
        WHERE event_id = ?
        AND user_id = ?
        """,
        (
            event_id,
            user_id,
        ),
    ).fetchone()

    if existing:
        return

    conn.execute(
        """
        INSERT INTO favorites (
            event_id,
            user_id,
            created_at
        )
        VALUES (?, ?, ?)
        """,
        (
            event_id,
            user_id,
            now_iso(),
        ),
    )


def seed():
    init_db(DB_PATH)
    migrate_db(DB_PATH)

    conn = get_db_connection(DB_PATH)

    user_ids = []

    for user in DEMO_USERS:
        user_id = get_or_create_user(
            conn,
            user["name"],
            user["email"],
        )

        user_ids.append(user_id)

    event_ids = []

    for index, event in enumerate(DEMO_EVENTS):

        owner_id = user_ids[
            index % len(user_ids)
        ]

        event_id = get_or_create_event(
            conn,
            owner_id,
            event,
        )

        event_ids.append(
            (
                event_id,
                owner_id,
                event,
            )
        )

    conn.commit()

    random.seed(42)

    for event_id, owner_id, event in event_ids:

        if event["status"] == "cancelled":
            continue

        possible_attendees = [
            user_id
            for user_id in user_ids
            if user_id != owner_id
        ]

        random.shuffle(
            possible_attendees
        )

        max_demo_rsvps = min(
            len(possible_attendees),
            max(
                3,
                min(
                    event["max_guests"],
                    random.randint(4, 7),
                ),
            ),
        )

        selected_users = possible_attendees[
            :max_demo_rsvps
        ]

        for index, user_id in enumerate(
            selected_users
        ):

            if (
                event["max_guests"] <= 5
                and index >= event["max_guests"]
            ):
                status = "waitlist"
            else:
                status = "going"

            checked_in = 0

            if status == "going":
                checked_in = random.choice(
                    [0, 0, 1]
                )

            add_rsvp(
                conn,
                event_id,
                user_id,
                status,
                checked_in,
            )

        favorite_users = possible_attendees[:3]

        for user_id in favorite_users:
            add_favorite(
                conn,
                event_id,
                user_id,
            )

    conn.commit()
    conn.close()

    print()
    print("Demo data added successfully.")
    print()
    print("Demo login accounts:")
    print("--------------------")

    for user in DEMO_USERS:
        print(
            f"{user['email']}  |  password: demo123"
        )

    print()
    print(
        f"Created/verified {len(DEMO_USERS)} demo users "
        f"and {len(DEMO_EVENTS)} demo events."
    )


if __name__ == "__main__":
    seed()