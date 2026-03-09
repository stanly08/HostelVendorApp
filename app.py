import os
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, request, flash, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# Security configuration
app.config['SECRET_KEY'] = '8b89f32a3a528957f6542e1879064c8de8be55b4cc4a43c2'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel_vendor.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# DATABASE MODELS

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # Stores the HASHED password

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, default=0)

class Debt(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date_added = db.Column(db.DateTime, default=datetime.utcnow)
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    product = db.relationship('Product', backref='debts')

 # user authentication

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'error')
            return redirect(url_for('signup'))

        # Securely hash the password before saving to SQLite
        hashed_pw = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(username=username, password=hashed_pw)
        
        db.session.add(new_user)
        db.session.commit()
        flash('Account created! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            session['user_id'] = user.id
            session['username'] = user.username
            return redirect(url_for('dashboard'))
        
        flash('Invalid username or password', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))



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
        flash(f'Added {new_prod.name} to inventory.', 'success')
        
    products = Product.query.all()
    return render_template('inventory.html', products=products)

@app.route('/add_debt', methods=['POST'])
def add_debt():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    prod_id = request.form['product_id']
    qty = int(request.form['quantity'])
    product = Product.query.get(prod_id)
    
    if product and product.stock >= qty:
        
        product.stock -= qty 
        total_price = product.price * qty
        
        new_debt = Debt(
            customer_name=request.form['customer'],
            phone=request.form['phone'],
            amount=total_price,
            product_id=prod_id
        )
        db.session.add(new_debt)
        db.session.commit()
        flash(f'Debt of KES {total_price} recorded for {request.form["customer"]}', 'success')
    else:
        flash('Error: Insufficient stock available!', 'error')
        
    return redirect(url_for('dashboard'))

@app.route('/debts')
def view_debts():
    if 'user_id' not in session: return redirect(url_for('login'))
    debts = Debt.query.order_by(Debt.date_added.desc()).all()
    total_owed = db.session.query(func.sum(Debt.amount)).scalar() or 0
    return render_template('debts.html', debts=debts, total_owed=total_owed)

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    total_debt = db.session.query(func.sum(Debt.amount)).scalar() or 0
    low_stock_items = Product.query.filter(Product.stock < 5).all()
    all_products = Product.query.all()
    inventory_value = sum(p.price * p.stock for p in all_products)
    
    return render_template('reports.html', 
                           total_debt=total_debt, 
                           low_stock=len(low_stock_items), 
                           inventory_value=inventory_value,
                           low_stock_list=low_stock_items)

# APP INITIALIZATION

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # this automatically generates the .db file and tables
    app.run(debug=True, host='0.0.0.0', port=5000)
