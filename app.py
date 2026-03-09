import os
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, render_template, redirect, url_for, request, flash, session, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from fpdf import FPDF

# Load the variables from .env
load_dotenv()

app = Flask(__name__)

# pulling the key using os.environ
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- DATABASE MODELS ---

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) 

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

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    product_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    date_sold = db.Column(db.DateTime, default=datetime.utcnow)
    customer_name = db.Column(db.String(100), default="Cash Customer")

# --- AUTHENTICATION ---

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

# --- CORE LOGIC & POS ---

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

@app.route('/process_transaction', methods=['POST'])
def process_transaction():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    prod_id = request.form['product_id']
    qty = int(request.form['quantity'])
    action = request.form['action'] 
    product = Product.query.get(prod_id)
    
    if not product or product.stock < qty:
        flash('Error: Insufficient stock available!', 'error')
        return redirect(url_for('dashboard'))

    total_price = product.price * qty
    product.stock -= qty 

    if action == 'debt':
        new_debt = Debt(
            customer_name=request.form['customer'],
            phone=request.form['phone'],
            amount=total_price,
            product_id=prod_id
        )
        db.session.add(new_debt)
        flash(f'Debt of KES {total_price} recorded for {request.form["customer"]}', 'success')
    else:
        new_sale = Sale(
            product_name=product.name,
            amount=total_price,
            quantity=qty,
            customer_name="Cash Customer"
        )
        db.session.add(new_sale)
        flash(f'Direct sale of {product.name} (KES {total_price}) completed!', 'success')

    db.session.commit()
    return redirect(url_for('dashboard'))

@app.route('/debts')
def view_debts():
    if 'user_id' not in session: return redirect(url_for('login'))
    debts = Debt.query.order_by(Debt.date_added.desc()).all()
    total_owed = db.session.query(func.sum(Debt.amount)).scalar() or 0
    return render_template('debts.html', debts=debts, total_owed=total_owed)

@app.route('/clear_debt/<int:debt_id>')
def clear_debt(debt_id):
    if 'user_id' not in session: return redirect(url_for('login'))
    debt = Debt.query.get_or_404(debt_id)
    new_sale = Sale(
        product_name=debt.product.name if debt.product else "Unknown Product",
        amount=debt.amount,
        quantity=1, 
        customer_name=debt.customer_name
    )
    db.session.add(new_sale)
    db.session.delete(debt)
    db.session.commit()
    flash(f'Debt for {debt.customer_name} cleared and recorded as a Sale!', 'success')
    return redirect(url_for('view_debts'))

@app.route('/reports')
def reports():
    if 'user_id' not in session: return redirect(url_for('login'))
    total_debt = db.session.query(func.sum(Debt.amount)).scalar() or 0
    total_sales_revenue = db.session.query(func.sum(Sale.amount)).scalar() or 0
    low_stock_items = Product.query.filter(Product.stock < 5).all()
    all_products = Product.query.all()
    inventory_value = sum(p.price * p.stock for p in all_products)
    return render_template('reports.html', 
                           total_debt=total_debt, 
                           total_sales=total_sales_revenue,
                           low_stock=len(low_stock_items), 
                           inventory_value=inventory_value,
                           low_stock_list=low_stock_items)

@app.route('/download_report')
def download_report():
    if 'user_id' not in session: return redirect(url_for('login'))
    
    total_debt = db.session.query(func.sum(Debt.amount)).scalar() or 0
    total_sales = db.session.query(func.sum(Sale.amount)).scalar() or 0
    
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "Hostel Vendor App - Financial Report", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=12)
    pdf.cell(190, 10, f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(5)
    pdf.cell(190, 10, f"Total Cash Sales: KES {total_sales}", ln=True)
    pdf.cell(190, 10, f"Total Outstanding Debt: KES {total_debt}", ln=True)
    
    response = make_response(pdf.output(dest='S'))
    response.headers.set('Content-Disposition', 'attachment', filename='sales_report.pdf')
    response.headers.set('Content-Type', 'application/pdf')
    return response

# --- APP INITIALIZATION ---

if __name__ == '__main__':
    with app.app_context():
        db.create_all() 
    app.run(debug=True, host='0.0.0.0', port=5000)
