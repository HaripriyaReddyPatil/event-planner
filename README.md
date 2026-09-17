# Event Planner

Event Planner is a Flask web application for creating events, managing RSVPs, and keeping track of attendance.

I built it to practice full-stack development with Flask, SQLite, HTML, CSS, and Jinja templates.

## Live Demo

[View the live application](https://event-planner-cpoq.onrender.com)

## Features

### For attendees

- Create an account and log in
- Browse upcoming events
- Search by event name, description, or location
- Filter events by category
- Sort events by date, popularity, or newest
- RSVP to an event
- Join a waitlist when an event is full
- Cancel an RSVP
- Save events for later
- Download an event to a calendar using an `.ics` file
- View joined and saved events from the dashboard

### For organizers

- Create, edit, copy, and delete events
- Add event category, date, time, location, description, and capacity
- View RSVP counts and waitlist counts
- Check attendees in
- Track event fill rate and check-in rate
- Export the attendee list as a CSV file
- View confirmed guests and waitlisted guests

## Tech Stack

- Python
- Flask
- SQLite
- HTML
- CSS
- Jinja2
- Werkzeug

## Project Structure

```text
event_planner/
├── app.py
├── requirements.txt
├── render.yaml
├── static/
│   └── style.css
└── templates/
    ├── analytics.html
    ├── base.html
    ├── dashboard.html
    ├── error.html
    ├── event_detail.html
    ├── event_form.html
    ├── home.html
    ├── login.html
    └── register.html
```

## Run Locally

Create a virtual environment:

```bash
python3 -m venv venv
source venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the app:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The SQLite database is created the first time the app runs.

## Deployment

The project includes a `render.yaml` file for Render.

Build command:

```text
pip install -r requirements.txt
```

Start command:

```text
gunicorn app:app
```

A `SECRET_KEY` environment variable should be added in the hosting settings.

## Things I would add next

- PostgreSQL for persistent cloud storage
- Email confirmations
- Password reset
- Event image uploads
- QR code check-in
- Reminder emails
- Pagination
- Tests
