from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from mpesa_utils import trigger_stk_push

app = Flask(__name__)
app.secret_key = "zetech_research_2026_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel_ledger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# --- DATABASE MODELS ---
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    sales = db.relationship('Sale', backref='owner', lazy=True)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False)
    payment_status = db.Column(db.String(20), default='Unpaid')
    checkout_id = db.Column(db.String(100), nullable=True)
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTHENTICATION ROUTES ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        new_user = User(username=request.form.get('username'), 
                        business_name=request.form.get('business_name'), 
                        password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            login_user(user)
            return redirect(url_for('index'))
        flash("Login failed. Check credentials.", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# --- SALES MANAGEMENT (CRUD) ---
@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('landing.html')
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.date_created.desc()).all()
    total_sales = sum(s.amount for s in sales)
    total_debt = sum(s.amount for s in sales if s.payment_status == 'Unpaid')
    return render_template('index.html', sales=sales, total_sales=total_sales, total_debt=total_debt)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    if request.method == 'POST':
        new_sale = Sale(item_name=request.form['item_name'], amount=float(request.form['amount']),
                        customer_name=request.form['customer_name'], customer_phone=request.form['customer_phone'],
                        payment_status=request.form['payment_status'], user_id=current_user.id)
        db.session.add(new_sale)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_sale.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id != current_user.id:
        return redirect(url_for('index'))
    if request.method == 'POST':
        sale.item_name, sale.amount = request.form['item_name'], float(request.form['amount'])
        sale.customer_name, sale.customer_phone = request.form['customer_name'], request.form['customer_phone']
        sale.payment_status = request.form['payment_status']
        db.session.commit()
        flash("Record updated!", "success")
        return redirect(url_for('index'))
    return render_template('edit_sale.html', sale=sale)

@app.route('/delete/<int:id>')
@login_required
def delete_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id == current_user.id:
        db.session.delete(sale)
        db.session.commit()
        flash("Record deleted.", "info")
    return redirect(url_for('index'))

# --- M-PESA INTEGRATION ---
@app.route('/stk_push/<int:id>')
@login_required
def stk_push_route(id):
    sale = Sale.query.get_or_404(id)
    callback_url = "https://your-render-app-name.onrender.com/mpesa_callback"
    response = trigger_stk_push(sale.customer_phone, int(sale.amount), callback_url)
    if response.get('ResponseCode') == '0':
        sale.checkout_id = response.get('CheckoutRequestID')
        db.session.commit()
        flash("Payment prompt sent!", "success")
    else:
        flash("M-PESA error. Check phone format.", "danger")
    return redirect(url_for('index'))

@app.route('/mpesa_callback', methods=['POST'])
def mpesa_callback():
    data = request.get_json()
    res_code = data['Body']['stkCallback']['ResultCode']
    checkout_id = data['Body']['stkCallback']['CheckoutRequestID']
    if res_code == 0:
        sale = Sale.query.filter_by(checkout_id=checkout_id).first()
        if sale:
            sale.payment_status = 'Paid'
            db.session.commit()
    return jsonify({"ResultCode": 0, "ResultDesc": "Success"})

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)