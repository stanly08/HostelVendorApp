Sales System for Snacks and Juices

Project Overview

The Sales System for Snacks and Juices is a digital solution designed to help student entrepreneurs in college hostels transition from manual, error-prone record-keeping to a secure, automated system.
It addresses the core challenges of financial instability and payment disputes by providing real-time inventory tracking and automated customer debt management specifically for snack and juice ventures.

Key Features

1. User Authentication: Secure Sign-up and Login for vendors to protect business data and ensure data integrity.

2. Inventory Management: Automatic stock deduction during sales of juices or snacks and a module for restocking to prevent stock-outs.

3. Debt Tracking: A digital ledger to record credit sales and monitor outstanding balances, moving away from unreliable physical notebooks.

4. Automated Reminders: One-click WhatsApp integration to send payment reminders to customers, reducing the burden of manual follow-ups.

5. Business Analytics: Automated reports on total debt, inventory value, and low-stock alerts to support informed decision-making.

Technical Stack

Backend: Python 3 using the Flask framework for lightweight web server logic and transaction processing.

Database: SQLite managed via SQLAlchemy (ORM) for reliable, tamper-proof, and local data storage.

Frontend: HTML5 and CSS3 optimized for mobile accessibility on student smartphones.

Payment Integration: Safaricom Daraja API (M-Pesa STK Push) capability for automated transaction handling in the hostel environment.







Installation & Setup

1. Open your terminal in your development environment:

```
cd SalesSystemSnacksJuices

```
2. Set Up Virtual Environment

```
python -m venv venv
# Activate on Windows:
venv\Scripts\activate
# Activate on Mac/Linux:
source venv/bin/activate
```

3. Install Dependencies
   
   Install the required libraries listed in requirements.txt:

```
pip install -r requirements.txt
```

4. Initialize the Database

   Run the application to generate the hostel_vendor.db file automatically:

```
python app.py
```


Below is the complete project structure

```
HostelVendorApp/
├── app.py              # The main "brain" of the project (Routes, Models, & Logic)
├── requirements.txt    # List of Python libraries to install
├── hostel_vendor.db    # The SQLite database (generated automatically)
├── static/             
│   └── style.css       # styling and layout
└── templates/          # HTML pages
    ├── login.html      # Authentication entry
    ├── signup.html     # User registration
    ├── dashboard.html  # Main vendor console
    ├── inventory.html  # Stock management page
    ├── debts.html      # Customer debt ledger
    └── reports.html    # Business performance summaries
```
