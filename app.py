from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "research_project_2026_secret"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///vendor_data.db'
db = SQLAlchemy(app)

# Authentication Setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

# GMAIL CONFIGURATION
# Replace with your Gmail and the 16-digit App Password
EMAIL_ADDRESS = 'anasistanly@gmail.com'
EMAIL_PASSWORD = 'ooyk yygp posx caba' 

# Database Models
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    business_name = db.Column(db.String(150), nullable=False)
    sales = db.relationship('Sale', backref='owner', lazy=True)

class Sale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    item_name = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20), nullable=False) # Important for WhatsApp
    customer_email = db.Column(db.String(120))
    payment_status = db.Column(db.String(20), default='Unpaid')
    date_created = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# --- ROUTES ---

@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('landing.html')
    
    sales = Sale.query.filter_by(user_id=current_user.id).order_by(Sale.date_created.desc()).all()
    total_sales = sum(s.amount for s in sales)
    total_debt = sum(s.amount for s in sales if s.payment_status == 'Unpaid')
    return render_template('index.html', sales=sales, total_sales=total_sales, total_debt=total_debt)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        hashed_pw = generate_password_hash(request.form['password'], method='pbkdf2:sha256')
        new_user = User(
            username=request.form['username'], 
            password=hashed_pw, 
            business_name=request.form['business_name']
        )
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please login.", "success")
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash("Invalid Username or Password", "danger")
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/add', methods=['GET', 'POST'])
@login_required
def add_sale():
    if request.method == 'POST':
        new_sale = Sale(
            item_name=request.form['item_name'], 
            amount=float(request.form['amount']),
            customer_name=request.form['customer_name'], 
            customer_phone=request.form['customer_phone'],
            customer_email=request.form['customer_email'], 
            payment_status=request.form['payment_status'],
            user_id=current_user.id
        )
        db.session.add(new_sale)
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('add_sale.html')

@app.route('/pay/<int:id>')
@login_required
def mark_as_paid(id):
    sale = Sale.query.get_or_404(id)
    if sale.user_id == current_user.id:
        sale.payment_status = 'Paid'
        db.session.commit()
    return redirect(url_for('index'))

@app.route('/email_remind/<int:id>')
@login_required
def email_remind(id):
    sale = Sale.query.get_or_404(id)
    try:
        msg = EmailMessage()
        msg.set_content(f"Hi {sale.customer_name}, This is a kind reminder for your payment of KES {sale.amount} for {sale.item_name} at {current_user.business_name}. Kindly purpose to clear your outstanding balance. BEST REGARDS!!")
        msg['Subject'] = 'Payment Reminder'
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = sale.customer_email
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.send_message(msg)
        flash("Email Reminder Sent!", "success")
    except:
        flash("Failed to send email. Check your App Password.", "danger")
    return redirect(url_for('index'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)