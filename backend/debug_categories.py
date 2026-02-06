import requests
import json

base_url = "http://127.0.0.1:8000/api/v1"

# 1. Create Category
print("Creating Category...")
try:
    resp = requests.post(f"{base_url}/categories/", json={
        "name": "Electronics",
        "description": "Gadgets and stuff"
    })
    if resp.status_code == 200:
        cat = resp.json()
        print(f"Created: {cat['id']} - {cat['name']}")
        cat_id = cat['id']
    else:
        print(f"Create Failed: {resp.text}")
        exit()

    # 2. List Categories
    print("\nListing Categories...")
    resp = requests.get(f"{base_url}/categories/")
    cats = resp.json()
    print(f"Found {len(cats)} categories")

    # 3. Update Category
    print("\nUpdating Category...")
    resp = requests.put(f"{base_url}/categories/{cat_id}", json={
        "name": "Consumer Electronics"
    })
    print(f"Update Status: {resp.status_code}")
    print(f"New Name: {resp.json()['name']}")

except Exception as e:
    print(f"Error: {e}")
