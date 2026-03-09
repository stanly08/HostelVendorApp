import os
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'zetech_student_entrepreneur_2026'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel_vendor.db'
db = SQLAlchemy(app)

# DATABASE MODELS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0) # Essential for inventory tracking

class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False) # For WhatsApp reminders
    amount = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref='debts')

# AUTHENTICATION & CORE ROUTES

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'])
        new_user = User(username=request.form['username'], password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        flash('Invalid Credentials')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    products = Product.query.all()
    return render_template('dashboard.html', products=products)

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if 'user_id' not in session: return redirect(url_for('login'))
    if request.method == 'POST':
        new_prod = Product(
            name=request.form['name'],
            price=float(request.form['price']),
            stock=int(request.form['stock'])
        )
        db.session.add(new_prod)
        db.session.commit()
    products = Product.query.all()
    return render_template('inventory.html', products=products)

@app.route('/add_debt', methods=['POST'])
def add_debt():
    if 'user_id' not in session: return redirect(url_for('login'))
    prod_id = request.form['product_id']
    qty = int(request.form['quantity'])
    product = Product.query.get(prod_id)
    
    if product.stock >= qty:
        product.stock -= qty # Automatic inventory deduction
        new_debt = Debt(
            customer_name=request.form['customer'],
            phone=request.form['phone'],
            amount=product.price * qty,
            product_id=prod_id
        )
        db.session.add(new_debt)
        db.session.commit()
        flash('Debt Recorded Successfully')
    else:
        flash('Insufficient Stock!')
    return redirect(url_for('dashboard'))

@app.route('/debts')
def view_debts():
    if 'user_id' not in session: return redirect(url_for('login'))
    debts = Debt.query.all()
    total = sum(d.amount for d in debts)
    return render_template('debts.html', debts=debts, total_owed=total)

@app.route('/delete_debt/<int:id>')
def delete_debt(id):
    debt = Debt.query.get(id)
    db.session.delete(debt)
    db.session.commit()
    return redirect(url_for('view_debts'))

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    total_debt = db.session.query(func.sum(Debt.amount)).scalar() or 0
    low_stock = Product.query.filter(Product.stock < 5).count()
    products = Product.query.all()
    inv_value = sum(p.price * p.stock for p in products)
    return render_template('reports.html', total_debt=total_debt, low_stock=low_stock, inventory_value=inv_value)

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
