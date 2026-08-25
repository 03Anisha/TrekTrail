from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'trekking_secret_2024'
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

DB = 'trekking.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS admin (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        email TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS staff (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        experience TEXT,
        approval_status TEXT DEFAULT 'pending',
        status TEXT DEFAULT 'active',
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL,
        phone TEXT,
        emergency_contact TEXT,
        status TEXT DEFAULT 'active',
        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS treks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        location TEXT NOT NULL,
        difficulty TEXT NOT NULL,
        duration INTEGER NOT NULL,
        available_slots INTEGER NOT NULL,
        total_slots INTEGER NOT NULL,
        assigned_staff_id INTEGER,
        status TEXT DEFAULT 'pending',
        start_date DATE,
        end_date DATE,
        description TEXT,
        price REAL DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (assigned_staff_id) REFERENCES staff(id)
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        trek_id INTEGER NOT NULL,
        booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'booked',
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (trek_id) REFERENCES treks(id),
        UNIQUE(user_id, trek_id)
    )''')

    c.execute("SELECT COUNT(*) FROM admin")
    if c.fetchone()[0] == 0:
        c.execute("INSERT INTO admin (username, password, email) VALUES (?, ?, ?)",
                  ('admin', generate_password_hash('admin123'), 'admin@trekking.com'))

    conn.commit()
    conn.close()

# ─── Auth ────────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        role     = request.form['role']
        email    = request.form['email']
        password = request.form['password']
        conn = get_db()
        c    = conn.cursor()

        if role == 'admin':
            c.execute("SELECT * FROM admin WHERE username=?", (email,))
            user = c.fetchone()
            if user and check_password_hash(user['password'], password):
                session.update({'user_id': user['id'], 'role': 'admin', 'name': user['username']})
                conn.close()
                return redirect(url_for('admin_dashboard'))

        elif role == 'staff':
            c.execute("SELECT * FROM staff WHERE email=?", (email,))
            user = c.fetchone()
            if user and check_password_hash(user['password'], password):
                if user['status'] == 'blacklisted':
                    flash('Your account has been deactivated.', 'danger')
                elif user['approval_status'] != 'approved':
                    flash('Your account is awaiting admin approval.', 'warning')
                else:
                    session.update({'user_id': user['id'], 'role': 'staff', 'name': user['name']})
                    conn.close()
                    return redirect(url_for('staff_dashboard'))
                conn.close()
                return redirect(url_for('login'))

        elif role == 'user':
            c.execute("SELECT * FROM users WHERE email=?", (email,))
            user = c.fetchone()
            if user and check_password_hash(user['password'], password):
                if user['status'] == 'blacklisted':
                    flash('Your account has been deactivated.', 'danger')
                    conn.close()
                    return redirect(url_for('login'))
                session.update({'user_id': user['id'], 'role': 'user', 'name': user['name']})
                conn.close()
                return redirect(url_for('user_dashboard'))

        conn.close()
        flash('Invalid credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        role     = request.form['role']
        name     = request.form['name']
        email    = request.form['email']
        password = generate_password_hash(request.form['password'])
        phone    = request.form.get('phone', '')
        conn = get_db()
        c    = conn.cursor()
        try:
            if role == 'user':
                emergency = request.form.get('emergency_contact', '')
                c.execute("INSERT INTO users (name, email, password, phone, emergency_contact) VALUES (?,?,?,?,?)",
                          (name, email, password, phone, emergency))
                conn.commit()
                flash('Registration successful. You can now log in.', 'success')
            elif role == 'staff':
                experience = request.form.get('experience', '')
                c.execute("INSERT INTO staff (name, email, password, phone, experience) VALUES (?,?,?,?,?)",
                          (name, email, password, phone, experience))
                conn.commit()
                flash('Registration submitted. Please wait for admin approval.', 'success')
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('An account with this email already exists.', 'danger')
        finally:
            conn.close()
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

# ─── Admin ───────────────────────────────────────────────────────────────────

def admin_required():
    return session.get('role') == 'admin'

@app.route('/admin/dashboard')
def admin_dashboard():
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    stats = {
        'treks':        c.execute("SELECT COUNT(*) FROM treks").fetchone()[0],
        'users':        c.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        'staff':        c.execute("SELECT COUNT(*) FROM staff").fetchone()[0],
        'bookings':     c.execute("SELECT COUNT(*) FROM bookings").fetchone()[0],
        'pending_staff':c.execute("SELECT COUNT(*) FROM staff WHERE approval_status='pending'").fetchone()[0],
        'pending_treks':c.execute("SELECT COUNT(*) FROM treks WHERE status='pending'").fetchone()[0],
    }
    recent_bookings = c.execute("""
        SELECT b.*, u.name as user_name, t.name as trek_name
        FROM bookings b JOIN users u ON b.user_id=u.id JOIN treks t ON b.trek_id=t.id
        ORDER BY b.booking_date DESC LIMIT 5
    """).fetchall()
    conn.close()
    return render_template('admin/dashboard.html', stats=stats, recent_bookings=recent_bookings)

@app.route('/admin/treks')
def admin_treks():
    if not admin_required():
        return redirect(url_for('login'))
    search = request.args.get('search', '')
    conn = get_db()
    c    = conn.cursor()
    if search:
        treks = c.execute("""
            SELECT t.*, s.name as staff_name FROM treks t
            LEFT JOIN staff s ON t.assigned_staff_id=s.id
            WHERE t.name LIKE ? OR t.location LIKE ? OR CAST(t.id AS TEXT) LIKE ?
        """, (f'%{search}%', f'%{search}%', f'%{search}%')).fetchall()
    else:
        treks = c.execute("""
            SELECT t.*, s.name as staff_name FROM treks t
            LEFT JOIN staff s ON t.assigned_staff_id=s.id
        """).fetchall()
    all_staff = c.execute("SELECT * FROM staff WHERE approval_status='approved' AND status='active'").fetchall()
    conn.close()
    return render_template('admin/treks.html', treks=treks, all_staff=all_staff, search=search)

@app.route('/admin/trek/add', methods=['GET', 'POST'])
def admin_add_trek():
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    if request.method == 'POST':
        slots = int(request.form['available_slots'])
        c.execute("""INSERT INTO treks
            (name, location, difficulty, duration, available_slots, total_slots,
             assigned_staff_id, status, start_date, end_date, description, price)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request.form['name'], request.form['location'], request.form['difficulty'],
             int(request.form['duration']), slots, slots,
             request.form.get('assigned_staff_id') or None,
             request.form.get('status', 'pending'),
             request.form['start_date'], request.form['end_date'],
             request.form.get('description', ''),
             float(request.form.get('price', 0))))
        conn.commit()
        conn.close()
        flash('Trek created successfully.', 'success')
        return redirect(url_for('admin_treks'))
    all_staff = c.execute("SELECT * FROM staff WHERE approval_status='approved' AND status='active'").fetchall()
    conn.close()
    return render_template('admin/trek_form.html', trek=None, all_staff=all_staff)

@app.route('/admin/trek/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_trek(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    trek = c.execute("SELECT * FROM treks WHERE id=?", (id,)).fetchone()
    if request.method == 'POST':
        slots = int(request.form['available_slots'])
        c.execute("""UPDATE treks SET name=?, location=?, difficulty=?, duration=?,
            available_slots=?, total_slots=?, assigned_staff_id=?, status=?,
            start_date=?, end_date=?, description=?, price=? WHERE id=?""",
            (request.form['name'], request.form['location'], request.form['difficulty'],
             int(request.form['duration']), slots, int(request.form['total_slots']),
             request.form.get('assigned_staff_id') or None,
             request.form['status'],
             request.form['start_date'], request.form['end_date'],
             request.form.get('description', ''),
             float(request.form.get('price', 0)), id))
        conn.commit()
        conn.close()
        flash('Trek updated successfully.', 'success')
        return redirect(url_for('admin_treks'))
    all_staff = c.execute("SELECT * FROM staff WHERE approval_status='approved' AND status='active'").fetchall()
    conn.close()
    return render_template('admin/trek_form.html', trek=trek, all_staff=all_staff)

@app.route('/admin/trek/delete/<int:id>')
def admin_delete_trek(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    c.execute("DELETE FROM bookings WHERE trek_id=?", (id,))
    c.execute("DELETE FROM treks WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Trek deleted.', 'success')
    return redirect(url_for('admin_treks'))

@app.route('/admin/trek/assign/<int:trek_id>', methods=['POST'])
def admin_assign_staff(trek_id):
    if not admin_required():
        return redirect(url_for('login'))
    staff_id = request.form.get('staff_id') or None
    conn = get_db()
    c    = conn.cursor()
    c.execute("UPDATE treks SET assigned_staff_id=? WHERE id=?", (staff_id, trek_id))
    conn.commit()
    conn.close()
    flash('Staff assigned to trek.', 'success')
    return redirect(url_for('admin_treks'))

@app.route('/admin/staff')
def admin_staff():
    if not admin_required():
        return redirect(url_for('login'))
    search = request.args.get('search', '')
    conn = get_db()
    c    = conn.cursor()
    if search:
        staff = c.execute("""SELECT * FROM staff WHERE name LIKE ? OR CAST(id AS TEXT) LIKE ?""",
                          (f'%{search}%', f'%{search}%')).fetchall()
    else:
        staff = c.execute("SELECT * FROM staff").fetchall()
    conn.close()
    return render_template('admin/staff.html', staff=staff, search=search)

@app.route('/admin/staff/approve/<int:id>')
def admin_approve_staff(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE staff SET approval_status='approved' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Staff approved.', 'success')
    return redirect(url_for('admin_staff'))

@app.route('/admin/staff/reject/<int:id>')
def admin_reject_staff(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE staff SET approval_status='rejected' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Staff registration rejected.', 'success')
    return redirect(url_for('admin_staff'))

@app.route('/admin/staff/blacklist/<int:id>')
def admin_blacklist_staff(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE staff SET status='blacklisted' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Staff blacklisted.', 'success')
    return redirect(url_for('admin_staff'))

@app.route('/admin/staff/activate/<int:id>')
def admin_activate_staff(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE staff SET status='active' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('Staff reactivated.', 'success')
    return redirect(url_for('admin_staff'))

@app.route('/admin/users')
def admin_users():
    if not admin_required():
        return redirect(url_for('login'))
    search = request.args.get('search', '')
    conn = get_db()
    c    = conn.cursor()
    if search:
        users = c.execute("""SELECT * FROM users WHERE name LIKE ? OR CAST(id AS TEXT) LIKE ? OR phone LIKE ?""",
                          (f'%{search}%', f'%{search}%', f'%{search}%')).fetchall()
    else:
        users = c.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template('admin/users.html', users=users, search=search)

@app.route('/admin/users/blacklist/<int:id>')
def admin_blacklist_user(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE users SET status='blacklisted' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('User blacklisted.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/users/activate/<int:id>')
def admin_activate_user(id):
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    conn.execute("UPDATE users SET status='active' WHERE id=?", (id,))
    conn.commit()
    conn.close()
    flash('User reactivated.', 'success')
    return redirect(url_for('admin_users'))

@app.route('/admin/bookings')
def admin_bookings():
    if not admin_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    bookings = c.execute("""
        SELECT b.*, u.name as user_name, t.name as trek_name, t.location
        FROM bookings b JOIN users u ON b.user_id=u.id JOIN treks t ON b.trek_id=t.id
        ORDER BY b.booking_date DESC
    """).fetchall()
    conn.close()
    return render_template('admin/bookings.html', bookings=bookings)

# ─── Staff ───────────────────────────────────────────────────────────────────

def staff_required():
    return session.get('role') == 'staff'

@app.route('/staff/dashboard')
def staff_dashboard():
    if not staff_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    treks = c.execute("""
        SELECT t.*, COUNT(b.id) as booked_count
        FROM treks t LEFT JOIN bookings b ON t.id=b.trek_id AND b.status='booked'
        WHERE t.assigned_staff_id=?
        GROUP BY t.id
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('staff/dashboard.html', treks=treks)

@app.route('/staff/trek/<int:id>')
def staff_trek_detail(id):
    if not staff_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    trek = c.execute("SELECT * FROM treks WHERE id=? AND assigned_staff_id=?",
                     (id, session['user_id'])).fetchone()
    if not trek:
        flash('Trek not found or not assigned to you.', 'danger')
        conn.close()
        return redirect(url_for('staff_dashboard'))
    participants = c.execute("""
        SELECT b.*, u.name, u.email, u.phone, u.emergency_contact
        FROM bookings b JOIN users u ON b.user_id=u.id
        WHERE b.trek_id=?
    """, (id,)).fetchall()
    conn.close()
    return render_template('staff/trek_detail.html', trek=trek, participants=participants)

@app.route('/staff/trek/update/<int:id>', methods=['POST'])
def staff_update_trek(id):
    if not staff_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    trek = c.execute("SELECT * FROM treks WHERE id=? AND assigned_staff_id=?",
                     (id, session['user_id'])).fetchone()
    if not trek:
        flash('Unauthorized.', 'danger')
        conn.close()
        return redirect(url_for('staff_dashboard'))
    slots  = request.form.get('available_slots', trek['available_slots'])
    status = request.form.get('status', trek['status'])
    c.execute("UPDATE treks SET available_slots=?, status=? WHERE id=?", (slots, status, id))
    conn.commit()
    conn.close()
    flash('Trek updated.', 'success')
    return redirect(url_for('staff_trek_detail', id=id))

# ─── User ────────────────────────────────────────────────────────────────────

def user_required():
    return session.get('role') == 'user'

@app.route('/user/dashboard')
def user_dashboard():
    if not user_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    open_treks = c.execute("""
        SELECT t.*, s.name as staff_name FROM treks t
        LEFT JOIN staff s ON t.assigned_staff_id=s.id
        WHERE t.status='open'
    """).fetchall()
    my_bookings = c.execute("""
        SELECT b.*, t.name as trek_name, t.location, t.difficulty,
               t.start_date, t.end_date, t.status as trek_status
        FROM bookings b JOIN treks t ON b.trek_id=t.id
        WHERE b.user_id=?
        ORDER BY b.booking_date DESC
    """, (session['user_id'],)).fetchall()
    conn.close()
    return render_template('user/dashboard.html', open_treks=open_treks, my_bookings=my_bookings)

@app.route('/user/treks')
def user_treks():
    if not user_required():
        return redirect(url_for('login'))
    search     = request.args.get('search', '')
    difficulty = request.args.get('difficulty', '')
    location   = request.args.get('location', '')
    conn = get_db()
    c    = conn.cursor()
    query  = "SELECT t.*, s.name as staff_name FROM treks t LEFT JOIN staff s ON t.assigned_staff_id=s.id WHERE t.status='open'"
    params = []
    if search:
        query += " AND (t.name LIKE ? OR t.location LIKE ?)"
        params += [f'%{search}%', f'%{search}%']
    if difficulty:
        query += " AND t.difficulty=?"
        params.append(difficulty)
    if location:
        query += " AND t.location LIKE ?"
        params.append(f'%{location}%')
    treks = c.execute(query, params).fetchall()
    booked_ids = [r['trek_id'] for r in c.execute(
        "SELECT trek_id FROM bookings WHERE user_id=?", (session['user_id'],)).fetchall()]
    conn.close()
    return render_template('user/treks.html', treks=treks, booked_ids=booked_ids,
                           search=search, difficulty=difficulty, location=location)

@app.route('/user/book/<int:trek_id>')
def user_book_trek(trek_id):
    if not user_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    trek = c.execute("SELECT * FROM treks WHERE id=?", (trek_id,)).fetchone()
    if not trek or trek['status'] != 'open':
        flash('This trek is not available for booking.', 'danger')
        conn.close()
        return redirect(url_for('user_treks'))
    if trek['available_slots'] <= 0:
        flash('No slots available for this trek.', 'warning')
        conn.close()
        return redirect(url_for('user_treks'))
    try:
        c.execute("INSERT INTO bookings (user_id, trek_id) VALUES (?,?)",
                  (session['user_id'], trek_id))
        c.execute("UPDATE treks SET available_slots=available_slots-1 WHERE id=?", (trek_id,))
        conn.commit()
        flash('Trek booked successfully!', 'success')
    except sqlite3.IntegrityError:
        flash('You have already booked this trek.', 'warning')
    finally:
        conn.close()
    return redirect(url_for('user_dashboard'))

@app.route('/user/cancel/<int:booking_id>')
def user_cancel_booking(booking_id):
    if not user_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    booking = c.execute("SELECT * FROM bookings WHERE id=? AND user_id=?",
                        (booking_id, session['user_id'])).fetchone()
    if booking and booking['status'] == 'booked':
        c.execute("UPDATE bookings SET status='cancelled' WHERE id=?", (booking_id,))
        c.execute("UPDATE treks SET available_slots=available_slots+1 WHERE id=?", (booking['trek_id'],))
        conn.commit()
        flash('Booking cancelled.', 'success')
    else:
        flash('Cannot cancel this booking.', 'danger')
    conn.close()
    return redirect(url_for('user_dashboard'))

@app.route('/user/profile', methods=['GET', 'POST'])
def user_profile():
    if not user_required():
        return redirect(url_for('login'))
    conn = get_db()
    c    = conn.cursor()
    if request.method == 'POST':
        c.execute("UPDATE users SET name=?, phone=?, emergency_contact=? WHERE id=?",
                  (request.form['name'], request.form['phone'],
                   request.form['emergency_contact'], session['user_id']))
        conn.commit()
        session['name'] = request.form['name']
        flash('Profile updated.', 'success')
    user = c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],)).fetchone()
    conn.close()
    return render_template('user/profile.html', user=user)

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
