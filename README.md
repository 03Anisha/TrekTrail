<<<<<<< HEAD
# TrekTrail — Trekking Management Application

A role-based web application (Admin, Trek Staff, Trekker) for managing trekking activities: trek creation and approval, staff assignment, slot-based bookings, and trekking history — built with Flask, Jinja2, and SQLite.

## Features

- **Admin**: create/edit/remove treks, approve or blacklist trek staff, assign staff to treks, view/search all users, staff, and treks, blacklist users
- **Trek Staff**: register and log in (pending admin approval), view assigned treks, update available slots and trek status
- **Trekker**: register and log in, browse and filter treks by difficulty/location, book treks, view booking status and history
- Slot-based overbooking prevention
- Role-gated access — staff can only manage treks assigned to them; users can only book treks that are Open

## Tech Stack

- **Backend**: Python, Flask
- **Templating**: Jinja2
- **Database**: SQLite (schema created programmatically on first run)
- **Frontend**: HTML, CSS, Bootstrap

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

The SQLite database (`trekking.db`) is created automatically on first run — no manual DB setup required.

Visit `http://localhost:5000` once the server is running.

## Project Structure

```
trekking_app/
├── app.py                 # Flask app, routes, DB schema/init
├── requirements.txt
├── static/
│   ├── css/
│   └── uploads/
└── templates/
    ├── admin/
    ├── staff/
    ├── user/
    ├── base.html
    ├── index.html
    ├── login.html
    └── register.html
```

## Notes

This project was built as part of the IIT Madras Modern Application Development coursework. It later evolved into a decoupled Flask REST API + Vue.js SPA version with Redis caching and Celery background jobs — see [TrekTrail Pro](#) for that iteration.
=======
# TrekTrail
project python with flask api
>>>>>>> 803b59ca61694c84eee35874773151ec4c4e2fb3
