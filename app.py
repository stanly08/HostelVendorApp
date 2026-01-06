from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from mpesa_utils import trigger_stk_push

app = Flask(__name__)
app.secret_key = "zetech_research_2026_key"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostel_ledger.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- MAIL CONFIGURATION ---
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'anasistanly@gmail.com'  # Replace with your email
app.config['MAIL_PASSWORD'] = 'peam eest tymm xudz'    # Replace with your Gmail App Password
mail = Mail(app)

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
    customer_email = db.Column(db.String(120), nullable=True) # Restored for reminders
    payment_status = db.Column(db.String(20), default='Unpaid')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- AUTHENTICATION ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256')
        new_user = User(username=request.form.get('username'), business_name=request.form.get('business_name'), password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful!", "success")
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

# --- SALES & CRUD ---
@app.route('/')
def index():
    if not current_user.is_authenticated: return render_template('landing.html')
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.date_created.desc()).all()
    total_sales = sum(s.amount for s in sales)
    total_debt = sum(s.amount for s in sales if s.payment_status == 'Unpaid')
    return render_template('index.html', sales=sales, total_sales=total_sales, total_debt=total_debt)

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    if request.method == 'POST':
        new_sale = Sale(
            item_name=request.form['item_name'], amount=float(request.form['amount']),
            customer_name=request.form['customer_name'], customer_phone=request.form['customer_phone'],
            customer_email=request.form.get('customer_email'), # Capture email
            payment_status=request.form['payment_status'], user_id=current_user.id
        )
        db.session.add(new_sale)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_sale.html')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_sale(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id != current_user.id: return redirect(url_for('index'))
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

# --- REMINDERS & PAYMENTS ---
@app.route('/email_remind/<int:id>')
@login_required
def email_remind(id):
    sale = Sale.query.get_or_404(id)
    if not sale.customer_email:
        flash("No email address found for this customer.", "warning")
        return redirect(url_for('index'))
    try:
        msg = Message(subject=f"Payment Reminder: {current_user.business_name}", sender=app.config['MAIL_USERNAME'], recipients=[sale.customer_email])
        msg.body = f"Hi {sale.customer_name},\n\nThis is a kind reminder to clear your outstanding balance of KES {sale.amount} at {current_user.business_name}.\n\nTHANK YOU!!"
        mail.send(msg)
        flash(f"Reminder sent to {sale.customer_email}", "success")
    except Exception as e:
        flash(f"Email failed: {str(e)}", "danger")
    return redirect(url_for('index'))

@app.route('/stk_push/<int:id>')
@login_required
def stk_push_route(id):
    sale = Sale.query.get_or_404(id)
    response = trigger_stk_push(sale.customer_phone, int(sale.amount), f"Sale_{sale.id}")
    if response.get('success') == 'true':
        flash("M-PESA prompt sent!", "success")
    else:
        flash("M-PESA error.", "danger")
    return redirect(url_for('index'))

@app.route('/tinypesa_callback', methods=['POST'])
def tinypesa_callback():
    data = request.get_json()
    account_no = data.get('external_reference') 
    if account_no and account_no.startswith("Sale_"):
        sale_id = int(account_no.replace("Sale_", ""))
        sale = Sale.query.get(sale_id)
        if sale:
            sale.payment_status = 'Paid'
            db.session.commit()
    return jsonify({"status": "success"}), 200

if __name__ == '__main__':
    with app.app_context(): db.create_all()
    app.run(debug=True)