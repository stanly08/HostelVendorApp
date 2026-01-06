import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import base64

# CONFIGURATION (Replace with your Daraja Sandbox Credentials)
CONSUMER_KEY = 'your_consumer_key'
CONSUMER_SECRET = 'your_consumer_secret'
PASSKEY = 'your_sandbox_passkey'
BUSINESS_SHORTCODE = '174379'

def get_access_token():
    url = "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"
    r = requests.get(url, auth=HTTPBasicAuth(CONSUMER_KEY, CONSUMER_SECRET))
    return r.json().get('access_token')

def trigger_stk_push(phone, amount, callback_url):
    access_token = get_access_token()
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    # Password = Base64(ShortCode + Passkey + Timestamp)
    password_str = BUSINESS_SHORTCODE + PASSKEY + timestamp
    password = base64.b64encode(password_str.encode()).decode()
    
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {
        "BusinessShortCode": BUSINESS_SHORTCODE,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone, # Customer phone
        "PartyB": BUSINESS_SHORTCODE,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": "UniTrack",
        "TransactionDesc": "Payment for Goods"
    }
    
    response = requests.post("https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest", 
                             json=payload, headers=headers)
    return response.json()