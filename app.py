import os
from flask import Flask, request, redirect, url_for, render_template_string
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- MODELS ---

class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(50), default="Personal")

class Stats(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    visitor_count = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()
    if not Stats.query.first():
        db.session.add(Stats(visitor_count=0))
        db.session.commit()

# --- ROUTES ---

@app.route('/', methods=['GET', 'POST'])
def index():
    # 1. Visitor Counter
    stats = Stats.query.first()
    stats.visitor_count += 1
    db.session.commit()

    # 2. Search & Sort
    query = request.args.get('search', '')
    if query:
        contacts = Contact.query.filter(
            or_(Contact.name.contains(query), Contact.phone.contains(query))
        ).order_by(Contact.name.asc()).all()
    else:
        contacts = Contact.query.order_by(Contact.name.asc()).all()

    # 3. Add Contact
    if request.method == 'POST' and 'add_contact' in request.form:
        new_c = Contact(
            name=request.form['name'], 
            phone=request.form['phone'],
            category=request.form['category']
        )
        db.session.add(new_c)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template_string(TELEPHONE_BOOK_UI, 
                                 contacts=contacts, 
                                 query=query, 
                                 count=stats.visitor_count)

@app.route('/delete-bulk', methods=['POST'])
def delete_bulk():
    ids = request.form.getlist('contact_ids')
    if ids:
        Contact.query.filter(Contact.id.in_(ids)).delete(synchronize_session=False)
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_contact(id):
    contact = Contact.query.get_or_404(id)
    if request.method == 'POST':
        contact.name = request.form['name']
        contact.phone = request.form['phone']
        contact.category = request.form['category']
        db.session.commit()
        return redirect(url_for('index'))
    return render_template_string(EDIT_UI, contact=contact)

# --- UI TEMPLATES ---

TELEPHONE_BOOK_UI = '''
<!DOCTYPE html>
<html>
<head>
    <title>Digital Telephone Book</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <script>
        function toggleAll(source) {
            checkboxes = document.getElementsByName('contact_ids');
            for(var i in checkboxes) checkboxes[i].checked = source.checked;
        }

        function updateClock() {
            const now = new Date();
            document.getElementById('clock').textContent = now.toLocaleTimeString();
            const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
            document.getElementById('live-date').textContent = now.toLocaleDateString(undefined, options);
        }
        setInterval(updateClock, 1000);
    </script>
</head>
<body class="bg-light" onload="updateClock()">
<div class="container mt-5">
    <div class="row mb-3 gx-2 align-items-center">
        <div class="col-md-4"><span class="text-secondary small">📅 TODAY</span><div id="live-date" class="fw-bold"></div></div>
        <div class="col-md-4 text-center"><span class="text-secondary small">🕒 TIME</span><div id="clock" class="h4 text-primary fw-bold mb-0"></div></div>
        <div class="col-md-4 text-end"><span class="text-secondary small">👥 VISITORS</span><div><span class="badge bg-dark fs-6">{{ count }}</span></div></div>
    </div>

    <div class="card shadow">
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
            <h2 class="mb-0">📖 Telephone Book</h2>
            <span class="badge bg-light text-primary">{{ contacts|length }} Contacts</span>
        </div>
        <div class="card-body">
            <div class="row g-3 mb-4">
                <div class="col-md-5">
                    <form method="GET" class="d-flex">
                        <input type="text" name="search" class="form-control me-2" placeholder="Search..." value="{{ query }}">
                        <button class="btn btn-outline-primary" type="submit">Search</button>
                    </form>
                </div>
                <div class="col-md-7 text-end">
                    <button class="btn btn-success" data-bs-toggle="collapse" data-bs-target="#addForm">+ New Contact</button>
                </div>
            </div>

            <div id="addForm" class="collapse mb-4 p-3 border rounded bg-white">
                <form method="POST" class="row g-3">
                    <input type="hidden" name="add_contact" value="1">
                    <div class="col-md-4"><input type="text" name="name" class="form-control" placeholder="Full Name" required></div>
                    <div class="col-md-3"><input type="text" name="phone" class="form-control" placeholder="Phone Number" required></div>
                    <div class="col-md-3">
                        <select name="category" class="form-select">
                            <option>Personal</option><option>Work</option><option>Family</option><option>Emergency</option>
                        </select>
                    </div>
                    <div class="col-md-2"><button type="submit" class="btn btn-primary w-100">Save</button></div>
                </form>
            </div>

            <form action="/delete-bulk" method="POST" onsubmit="return confirm('Delete selected?')">
                <div class="table-responsive">
                    <table class="table table-hover align-middle">
                        <thead class="table-light">
                            <tr>
                                <th><input type="checkbox" onclick="toggleAll(this)"></th>
                                <th>Name</th><th>Phone</th><th>Category</th><th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for contact in contacts %}
                            <tr>
                                <td><input type="checkbox" name="contact_ids" value="{{ contact.id }}"></td>
                                <td class="fw-bold">{{ contact.name }}</td>
                                <td><a href="tel:{{ contact.phone }}" class="text-decoration-none">{{ contact.phone }}</a></td>
                                <td><span class="badge bg-info text-dark">{{ contact.category }}</span></td>
                                <td><a href="/edit/{{ contact.id }}" class="btn btn-sm btn-outline-secondary">Edit</a></td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                </div>
                {% if contacts %}
                <button type="submit" class="btn btn-danger mt-3">Delete Selected</button>
                {% endif %}
            </form>
        </div>
    </div>
</div>
<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>
'''

EDIT_UI = '''
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<div class="container mt-5"><div class="col-md-6 mx-auto card p-4 shadow">
    <h3>Edit Contact</h3>
    <form method="POST">
        <div class="mb-3"><label>Name</label><input type="text" name="name" class="form-control" value="{{ contact.name }}"></div>
        <div class="mb-3"><label>Phone</label><input type="text" name="phone" class="form-control" value="{{ contact.phone }}"></div>
        <div class="mb-3"><label>Category</label><select name="category" class="form-select">
            <option {% if contact.category == 'Personal' %}selected{% endif %}>Personal</option>
            <option {% if contact.category == 'Work' %}selected{% endif %}>Work</option>
            <option {% if contact.category == 'Family' %}selected{% endif %}>Family</option>
            <option {% if contact.category == 'Emergency' %}selected{% endif %}>Emergency</option>
        </select></div>
        <button type="submit" class="btn btn-primary">Update</button>
        <a href="/" class="btn btn-link text-secondary">Cancel</a>
    </form>
</div></div>
'''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)