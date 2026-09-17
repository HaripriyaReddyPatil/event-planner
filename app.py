from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, abort, Response
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import StringIO
import sqlite3
import csv
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DB_NAME = "event_planner.db"

CATEGORIES = [
    "Technology", "Academic", "Career", "Social",
    "Sports", "Arts", "Community", "Other"
]


def get_db():
    # Open one database connection for the current operation.
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    # Create the tables when the app runs for the first time.
    conn = get_db()

    conn.executescript("""
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
            created_at TEXT NOT NULL,
            FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS rsvps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'going',
            checked_in INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            UNIQUE(event_id, user_id),
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS favorites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(event_id, user_id),
            FOREIGN KEY(event_id) REFERENCES events(id) ON DELETE CASCADE,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
    """)

    conn.commit()
    conn.close()


def now_iso():
    return datetime.now().isoformat(timespec="seconds")


def current_user():
    # Use the user id stored in the session to load the signed-in user.
    user_id = session.get("user_id")
    if not user_id:
        return None

    conn = get_db()
    user = conn.execute(
        "SELECT id, name, email FROM users WHERE id = ?",
        (user_id,)
    ).fetchone()
    conn.close()
    return user


def login_required():
    if not session.get("user_id"):
        flash("Please log in to continue.", "warning")
        return False
    return True


def is_past(event_date, event_time):
    try:
        dt = datetime.strptime(
            f"{event_date} {event_time}",
            "%Y-%m-%d %H:%M"
        )
        return dt < datetime.now()
    except ValueError:
        return False


def event_stats(event_id):
    conn = get_db()

    event = conn.execute("""
        SELECT
            e.*,
            u.name AS organizer_name,
            SUM(CASE WHEN r.status = 'going' THEN 1 ELSE 0 END) AS going_count,
            SUM(CASE WHEN r.status = 'waitlist' THEN 1 ELSE 0 END) AS waitlist_count,
            SUM(CASE WHEN r.status = 'going' AND r.checked_in = 1 THEN 1 ELSE 0 END) AS checked_in_count
        FROM events e
        JOIN users u ON e.owner_id = u.id
        LEFT JOIN rsvps r ON e.id = r.event_id
        WHERE e.id = ?
        GROUP BY e.id
    """, (event_id,)).fetchone()

    conn.close()

    if event:
        event = dict(event)
        event["going_count"] = event["going_count"] or 0
        event["waitlist_count"] = event["waitlist_count"] or 0
        event["checked_in_count"] = event["checked_in_count"] or 0

    return event


def promote_waitlist(event_id):
    # If a confirmed guest cancels, move the first waitlisted user into the event.
    conn = get_db()
    event = conn.execute(
        "SELECT max_guests FROM events WHERE id = ?",
        (event_id,)
    ).fetchone()

    if not event:
        conn.close()
        return

    going_count = conn.execute("""
        SELECT COUNT(*) FROM rsvps
        WHERE event_id = ? AND status = 'going'
    """, (event_id,)).fetchone()[0]

    if going_count < event["max_guests"]:
        next_person = conn.execute("""
            SELECT id FROM rsvps
            WHERE event_id = ? AND status = 'waitlist'
            ORDER BY created_at ASC
            LIMIT 1
        """, (event_id,)).fetchone()

        if next_person:
            conn.execute(
                "UPDATE rsvps SET status = 'going' WHERE id = ?",
                (next_person["id"],)
            )
            conn.commit()

    conn.close()


@app.context_processor
def inject_globals():
    return {
        "logged_in_user": current_user(),
        "categories": CATEGORIES,
        "current_year": datetime.now().year,
    }


@app.route("/")
def home():
    q = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    sort = request.args.get("sort", "soonest")

    conn = get_db()

    query = """
        SELECT
            e.*,
            u.name AS organizer_name,
            SUM(CASE WHEN r.status = 'going' THEN 1 ELSE 0 END) AS going_count
        FROM events e
        JOIN users u ON e.owner_id = u.id
        LEFT JOIN rsvps r ON e.id = r.event_id
        WHERE 1=1
    """
    params = []

    if q:
        term = f"%{q}%"
        query += """
            AND (
                LOWER(e.title) LIKE LOWER(?)
                OR LOWER(e.description) LIKE LOWER(?)
                OR LOWER(e.location) LIKE LOWER(?)
            )
        """
        params.extend([term, term, term])

    if category:
        query += " AND e.category = ? "
        params.append(category)

    query += " GROUP BY e.id "

    if sort == "newest":
        query += " ORDER BY e.created_at DESC "
    elif sort == "popular":
        query += " ORDER BY going_count DESC, e.event_date, e.event_time "
    else:
        query += " ORDER BY e.event_date, e.event_time "

    events = [dict(row) for row in conn.execute(query, params).fetchall()]
    conn.close()

    for event in events:
        event["going_count"] = event["going_count"] or 0

    upcoming = [
        e for e in events
        if not is_past(e["event_date"], e["event_time"])
    ]

    return render_template(
        "home.html",
        events=upcoming,
        q=q,
        selected_category=category,
        sort=sort
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 6:
            flash("Use your name, email, and a password with at least 6 characters.", "error")
            return render_template("register.html")

        conn = get_db()
        exists = conn.execute(
            "SELECT id FROM users WHERE email = ?",
            (email,)
        ).fetchone()

        if exists:
            conn.close()
            flash("An account with this email already exists.", "error")
            return render_template("register.html")

        cursor = conn.execute("""
            INSERT INTO users (name, email, password_hash, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            name,
            email,
            generate_password_hash(password),
            now_iso()
        ))

        conn.commit()
        session["user_id"] = cursor.lastrowid
        conn.close()

        flash("Account created successfully.", "success")
        return redirect(url_for("dashboard"))

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ?",
            (email,)
        ).fetchone()
        conn.close()

        if not user or not check_password_hash(user["password_hash"], password):
            flash("Incorrect email or password.", "error")
            return render_template("login.html")

        session["user_id"] = user["id"]
        flash(f"Welcome back, {user['name'].split()[0]}.", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    if not login_required():
        return redirect(url_for("login"))

    user_id = session["user_id"]
    conn = get_db()

    created = [dict(row) for row in conn.execute("""
        SELECT
            e.*,
            SUM(CASE WHEN r.status = 'going' THEN 1 ELSE 0 END) AS going_count,
            SUM(CASE WHEN r.status = 'waitlist' THEN 1 ELSE 0 END) AS waitlist_count,
            SUM(CASE WHEN r.status = 'going' AND r.checked_in = 1 THEN 1 ELSE 0 END) AS checked_in_count
        FROM events e
        LEFT JOIN rsvps r ON e.id = r.event_id
        WHERE e.owner_id = ?
        GROUP BY e.id
        ORDER BY e.event_date, e.event_time
    """, (user_id,)).fetchall()]

    joined = [dict(row) for row in conn.execute("""
        SELECT e.*, u.name AS organizer_name, r.status
        FROM rsvps r
        JOIN events e ON r.event_id = e.id
        JOIN users u ON e.owner_id = u.id
        WHERE r.user_id = ?
        ORDER BY e.event_date, e.event_time
    """, (user_id,)).fetchall()]

    favorites = [dict(row) for row in conn.execute("""
        SELECT e.*, u.name AS organizer_name
        FROM favorites f
        JOIN events e ON f.event_id = e.id
        JOIN users u ON e.owner_id = u.id
        WHERE f.user_id = ?
        ORDER BY e.event_date, e.event_time
    """, (user_id,)).fetchall()]

    conn.close()

    for event in created:
        event["going_count"] = event["going_count"] or 0
        event["waitlist_count"] = event["waitlist_count"] or 0
        event["checked_in_count"] = event["checked_in_count"] or 0

    return render_template(
        "dashboard.html",
        created_events=created,
        joined_events=joined,
        favorite_events=favorites
    )


@app.route("/events/create", methods=["GET", "POST"])
def create_event():
    if not login_required():
        return redirect(url_for("login"))

    if request.method == "POST":
        data = {
            "title": request.form.get("title", "").strip(),
            "category": request.form.get("category", "Other"),
            "event_date": request.form.get("event_date", ""),
            "event_time": request.form.get("event_time", ""),
            "location": request.form.get("location", "").strip(),
            "description": request.form.get("description", "").strip(),
        }

        try:
            max_guests = int(request.form.get("max_guests", "0"))
        except ValueError:
            max_guests = 0

        if (
            not data["title"]
            or data["category"] not in CATEGORIES
            or not data["event_date"]
            or not data["event_time"]
            or not data["location"]
            or max_guests < 1
        ):
            flash("Please complete all required fields.", "error")
            return render_template("event_form.html", event=None)

        conn = get_db()
        cursor = conn.execute("""
            INSERT INTO events (
                owner_id, title, category, event_date, event_time,
                location, description, max_guests, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session["user_id"],
            data["title"],
            data["category"],
            data["event_date"],
            data["event_time"],
            data["location"],
            data["description"],
            max_guests,
            now_iso()
        ))

        conn.commit()
        event_id = cursor.lastrowid
        conn.close()

        flash("Event created successfully.", "success")
        return redirect(url_for("event_detail", event_id=event_id))

    return render_template("event_form.html", event=None)


@app.route("/events/<int:event_id>")
def event_detail(event_id):
    event = event_stats(event_id)
    if not event:
        abort(404)

    conn = get_db()

    attendees = conn.execute("""
        SELECT u.id, u.name, u.email, r.status, r.checked_in, r.created_at
        FROM rsvps r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
        ORDER BY
            CASE WHEN r.status = 'going' THEN 0 ELSE 1 END,
            r.created_at
    """, (event_id,)).fetchall()

    user_rsvp = None
    favorite = None

    if session.get("user_id"):
        user_rsvp = conn.execute("""
            SELECT * FROM rsvps
            WHERE event_id = ? AND user_id = ?
        """, (event_id, session["user_id"])).fetchone()

        favorite = conn.execute("""
            SELECT id FROM favorites
            WHERE event_id = ? AND user_id = ?
        """, (event_id, session["user_id"])).fetchone()

    conn.close()

    return render_template(
        "event_detail.html",
        event=event,
        attendees=attendees,
        user_rsvp=user_rsvp,
        favorite=favorite,
        event_is_past=is_past(event["event_date"], event["event_time"])
    )


@app.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
def edit_event(event_id):
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] != session["user_id"]:
        abort(403)

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        category = request.form.get("category", "Other")
        event_date = request.form.get("event_date", "")
        event_time = request.form.get("event_time", "")
        location = request.form.get("location", "").strip()
        description = request.form.get("description", "").strip()

        try:
            max_guests = int(request.form.get("max_guests", "0"))
        except ValueError:
            max_guests = 0

        if max_guests < event["going_count"]:
            flash(
                f"Guest limit cannot be below current attendance ({event['going_count']}).",
                "error"
            )
            return render_template("event_form.html", event=event)

        if (
            not title
            or category not in CATEGORIES
            or not event_date
            or not event_time
            or not location
            or max_guests < 1
        ):
            flash("Please complete all required fields.", "error")
            return render_template("event_form.html", event=event)

        conn = get_db()
        conn.execute("""
            UPDATE events
            SET title=?, category=?, event_date=?, event_time=?,
                location=?, description=?, max_guests=?
            WHERE id=?
        """, (
            title, category, event_date, event_time,
            location, description, max_guests, event_id
        ))
        conn.commit()
        conn.close()

        flash("Event updated.", "success")
        return redirect(url_for("event_detail", event_id=event_id))

    return render_template("event_form.html", event=event)


@app.route("/events/<int:event_id>/delete", methods=["POST"])
def delete_event(event_id):
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] != session["user_id"]:
        abort(403)

    conn = get_db()
    conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
    conn.commit()
    conn.close()

    flash("Event deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/events/<int:event_id>/clone", methods=["POST"])
def clone_event(event_id):
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] != session["user_id"]:
        abort(403)

    conn = get_db()
    cursor = conn.execute("""
        INSERT INTO events (
            owner_id, title, category, event_date, event_time,
            location, description, max_guests, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        session["user_id"],
        f"{event['title']} (Copy)",
        event["category"],
        event["event_date"],
        event["event_time"],
        event["location"],
        event["description"],
        event["max_guests"],
        now_iso()
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()

    flash("Event copied. Update the details before publishing.", "success")
    return redirect(url_for("edit_event", event_id=new_id))


@app.route("/events/<int:event_id>/rsvp", methods=["POST"])
def rsvp(event_id):
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] == session["user_id"]:
        flash("You are the organizer of this event.", "warning")
        return redirect(url_for("event_detail", event_id=event_id))

    if is_past(event["event_date"], event["event_time"]):
        flash("This event has already ended.", "error")
        return redirect(url_for("event_detail", event_id=event_id))

    status = "going" if event["going_count"] < event["max_guests"] else "waitlist"

    conn = get_db()
    try:
        conn.execute("""
            INSERT INTO rsvps (
                event_id, user_id, status, checked_in, created_at
            )
            VALUES (?, ?, ?, 0, ?)
        """, (
            event_id,
            session["user_id"],
            status,
            now_iso()
        ))
        conn.commit()
        if status == "going":
            flash("RSVP confirmed.", "success")
        else:
            flash("The event is full, so you were added to the waitlist.", "warning")
    except sqlite3.IntegrityError:
        flash("You already have an RSVP for this event.", "warning")
    finally:
        conn.close()

    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/cancel-rsvp", methods=["POST"])
def cancel_rsvp(event_id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    existing = conn.execute("""
        SELECT status FROM rsvps
        WHERE event_id = ? AND user_id = ?
    """, (event_id, session["user_id"])).fetchone()

    conn.execute("""
        DELETE FROM rsvps
        WHERE event_id = ? AND user_id = ?
    """, (event_id, session["user_id"]))

    conn.commit()
    conn.close()

    if existing and existing["status"] == "going":
        promote_waitlist(event_id)

    flash("Your RSVP has been cancelled.", "success")
    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/favorite", methods=["POST"])
def toggle_favorite(event_id):
    if not login_required():
        return redirect(url_for("login"))

    conn = get_db()
    existing = conn.execute("""
        SELECT id FROM favorites
        WHERE event_id = ? AND user_id = ?
    """, (event_id, session["user_id"])).fetchone()

    if existing:
        conn.execute("DELETE FROM favorites WHERE id = ?", (existing["id"],))
        flash("Removed from saved events.", "success")
    else:
        conn.execute("""
            INSERT INTO favorites (event_id, user_id, created_at)
            VALUES (?, ?, ?)
        """, (event_id, session["user_id"], now_iso()))
        flash("Event saved.", "success")

    conn.commit()
    conn.close()
    return redirect(url_for("event_detail", event_id=event_id))


@app.route("/events/<int:event_id>/analytics")
def analytics(event_id):
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] != session["user_id"]:
        abort(403)

    fill_rate = 0
    if event["max_guests"] > 0:
        fill_rate = round((event["going_count"] / event["max_guests"]) * 100)

    checkin_rate = 0
    if event["going_count"] > 0:
        checkin_rate = round((event["checked_in_count"] / event["going_count"]) * 100)

    conn = get_db()
    attendees = conn.execute("""
        SELECT u.id, u.name, u.email, r.status, r.checked_in, r.created_at
        FROM rsvps r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
        ORDER BY r.status, r.created_at
    """, (event_id,)).fetchall()
    conn.close()

    return render_template(
        "analytics.html",
        event=event,
        attendees=attendees,
        fill_rate=fill_rate,
        checkin_rate=checkin_rate
    )


@app.route("/events/<int:event_id>/check-in/<int:user_id>", methods=["POST"])
def toggle_checkin(event_id, user_id):
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] != session["user_id"]:
        abort(403)

    conn = get_db()
    attendee = conn.execute("""
        SELECT checked_in FROM rsvps
        WHERE event_id = ? AND user_id = ? AND status = 'going'
    """, (event_id, user_id)).fetchone()

    if attendee:
        new_value = 0 if attendee["checked_in"] else 1
        conn.execute("""
            UPDATE rsvps
            SET checked_in = ?
            WHERE event_id = ? AND user_id = ?
        """, (new_value, event_id, user_id))
        conn.commit()

    conn.close()
    return redirect(url_for("analytics", event_id=event_id))


@app.route("/events/<int:event_id>/export")
def export_attendees(event_id):
    # Build a CSV in memory so the organizer can download the attendee list.
    if not login_required():
        return redirect(url_for("login"))

    event = event_stats(event_id)
    if not event:
        abort(404)

    if event["owner_id"] != session["user_id"]:
        abort(403)

    conn = get_db()
    attendees = conn.execute("""
        SELECT u.name, u.email, r.status, r.checked_in, r.created_at
        FROM rsvps r
        JOIN users u ON r.user_id = u.id
        WHERE r.event_id = ?
        ORDER BY r.status, r.created_at
    """, (event_id,)).fetchall()
    conn.close()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Email", "Status", "Checked In", "RSVP Time"])

    for attendee in attendees:
        writer.writerow([
            attendee["name"],
            attendee["email"],
            attendee["status"],
            "Yes" if attendee["checked_in"] else "No",
            attendee["created_at"]
        ])

    filename = f"event_{event_id}_attendees.csv"

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


@app.route("/events/<int:event_id>/calendar")
def calendar_download(event_id):
    # Create a basic iCalendar file that can be opened by calendar apps.
    event = event_stats(event_id)
    if not event:
        abort(404)

    start = datetime.strptime(
        f"{event['event_date']} {event['event_time']}",
        "%Y-%m-%d %H:%M"
    )

    dtstart = start.strftime("%Y%m%dT%H%M%S")
    safe_description = (event["description"] or "").replace("\n", "\\n")

    ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Event Planner//EN
BEGIN:VEVENT
UID:event-{event_id}@eventplanner
DTSTAMP:{datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")}
DTSTART:{dtstart}
SUMMARY:{event["title"]}
LOCATION:{event["location"]}
DESCRIPTION:{safe_description}
END:VEVENT
END:VCALENDAR
"""

    return Response(
        ics,
        mimetype="text/calendar",
        headers={
            "Content-Disposition": f'attachment; filename="event_{event_id}.ics"'
        }
    )


@app.errorhandler(403)
def forbidden(_error):
    return render_template(
        "error.html",
        code=403,
        title="Access denied",
        message="You do not have permission to perform this action."
    ), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template(
        "error.html",
        code=404,
        title="Page not found",
        message="The page or event you are looking for does not exist."
    ), 404


# Make sure the database tables exist when the app starts.
init_db()

if __name__ == "__main__":
    app.run(debug=True)
