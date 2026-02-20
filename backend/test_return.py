import requests

# 1. Login to get token
resp = requests.post("http://localhost:8000/api/v1/login/access-token", data={
    "username": "admin@lumefy.com",  # typical seed user
    "password": "admin"
})
if resp.status_code != 200:
    print("Login failed:", resp.text)
    
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# 2. Get a sale to return (delivered or completed)
sales = requests.get("http://localhost:8000/api/v1/sales/?status=DELIVERED", headers=headers).json()
if not sales:
    sales = requests.get("http://localhost:8000/api/v1/sales/?status=COMPLETED", headers=headers).json()

if not sales:
    print("No DELIVERED or COMPLETED sales found. Please make sure there is one to return.")
else:
    sale = sales[0]
    # get sale details
    sale_detail = requests.get(f"http://localhost:8000/api/v1/sales/{sale['id']}", headers=headers).json()
    
    # create return payload
    items = []
    for item in sale_detail['items']:
        items.append({
            "sale_item_id": item['id'],
            "quantity": 1
        })
        break # just return 1 item
        
    payload = {
        "sale_id": sale['id'],
        "reason": "Test backend script",
        "notes": "Testing",
        "items": items
    }
    
    # 3. Try to create return
    res = requests.post("http://localhost:8000/api/v1/returns", json=payload, headers=headers)
    print("Status:", res.status_code)
    print("Response:", res.text)
