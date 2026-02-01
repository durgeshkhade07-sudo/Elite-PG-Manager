import os, io
from flask import Flask, render_template, request, redirect, url_for, send_file
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

app = Flask(__name__)

# --- DB CONFIG ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pg_management.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

db = SQLAlchemy(app)

# --- DATABASE MODEL ---
class Tenant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15)) 
    room_no = db.Column(db.String(10))
    rent_amount = db.Column(db.Float, default=0.0)
    unit_rate = db.Column(db.Float, default=10.0) 
    last_reading = db.Column(db.Float, default=0.0)
    current_reading = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='Pending') 

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    tenants = Tenant.query.all()
    for t in tenants:
        t.units = max(0, t.current_reading - t.last_reading)
        t.total = t.rent_amount + (t.units * t.unit_rate)
    
    paid = sum(t.rent_amount for t in tenants if t.status == 'Paid')
    pending = sum(t.rent_amount for t in tenants if t.status == 'Pending')
    return render_template('index.html', tenants=tenants, paid=paid, pending=pending)

@app.route('/add', methods=['GET', 'POST'])
def add():
    if request.method == 'POST':
        db.session.add(Tenant(
            name=request.form.get('name'),
            phone=request.form.get('phone'),
            room_no=request.form.get('room_no'),
            rent_amount=float(request.form.get('rent', 0)),
            last_reading=float(request.form.get('reading', 0)),
            current_reading=float(request.form.get('reading', 0))
        ))
        db.session.commit()
        return redirect('/')
    return render_template('add_tenant.html')

@app.route('/update_reading/<int:id>', methods=['POST'])
def update(id):
    t = Tenant.query.get(id)
    t.current_reading = float(request.form.get('new_reading', t.current_reading))
    db.session.commit()
    return redirect('/')

@app.route('/toggle/<int:id>')
def toggle(id):
    t = Tenant.query.get(id)
    if t.status == 'Pending':
        t.status = 'Paid'
        t.last_reading = t.current_reading
    else:
        t.status = 'Pending'
    db.session.commit()
    return redirect('/')

@app.route('/receipt/<int:id>')
def receipt(id):
    t = Tenant.query.get(id)
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica-Bold", 24)
    p.drawString(100, 750, "ELITE PG RENT RECEIPT")
    p.setFont("Helvetica", 14)
    p.drawString(100, 710, f"Tenant: {t.name} | Room: {t.room_no}")
    p.drawString(100, 680, f"Phone: {t.phone}")
    p.line(100, 670, 500, 670)
    p.drawString(100, 640, f"Rent: Rs. {t.rent_amount}")
    p.drawString(100, 620, f"Elec Units: {t.current_reading - t.last_reading}")
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 580, f"Total Amount Paid: Rs. {t.rent_amount + (t.current_reading - t.last_reading)*10}")
    p.showPage()
    p.save()
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=f"{t.name}_receipt.pdf")

@app.route('/delete/<int:id>')
def delete(id):
    db.session.delete(Tenant.query.get(id))
    db.session.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)