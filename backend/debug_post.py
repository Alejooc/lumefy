import requests
import json

url = "http://127.0.0.1:8000/api/v1/products/"
payload = {
    "name": "Test Product",
    "price": 100,
    "cost": 50,
    "track_inventory": True,
    "min_stock": 10
}

try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    try:
        err = response.json()
        detail = err.get("detail", response.text)
        import re
        match = re.search(r"expression '.*?' failed to locate a name \('.*?'\)", detail)
        if match:
            print("FOUND CAUSE:", match.group(0))
        else:
            print("DETAIL (start):", detail[:100])
    except:
        print("Response Text:", response.text)
except Exception as e:
    print(f"Request failed: {e}")
