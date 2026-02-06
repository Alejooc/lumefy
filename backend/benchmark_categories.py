import requests
import time

url = "http://127.0.0.1:8000/api/v1/categories/"
print(f"Testing {url}")

start = time.time()
try:
    resp = requests.get(url)
    elapsed = time.time() - start
    print(f"Status: {resp.status_code}")
    print(f"Time: {elapsed:.4f} seconds")
    print(f"Count: {len(resp.json())}")
except Exception as e:
    print(f"Error: {e}")
