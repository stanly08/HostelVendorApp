import requests

TINYPESA_API_KEY = 'your_tinypesa_api_key' # Get from tinypesa.com

def trigger_stk_push(phone, amount, account_no="UniTrack"):
    url = "https://tinypesa.com/api/v1/express/initialize"
    headers = {"ApiKey": TINYPESA_API_KEY, "Content-Type": "application/x-www-form-urlencoded"}
    payload = {"amount": amount, "msisdn": phone, "account_no": account_no}
    response = requests.post(url, data=payload, headers=headers)
    return response.json()