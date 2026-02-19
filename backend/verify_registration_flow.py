import requests
import sys

BASE_URL = "http://127.0.0.1:8000/api/v1"
EMAIL = "test_expiry_fail@example.com"
PASSWORD = "password12345"

def test_flow():
    # 1. Login
    print(f"Logging in as {EMAIL}...")
    try:
        resp = requests.post(f"{BASE_URL}/login/access-token", data={
            "username": EMAIL,
            "password": PASSWORD
        })
        if resp.status_code != 200:
            print(f"Login failed: {resp.status_code} {resp.text}")
            return
        
        token = resp.json()["access_token"]
        print("Login success. Token received.")
        headers = {"Authorization": f"Bearer {token}"}
    except Exception as e:
        print(f"Login exception: {e}")
        return

    # 2. Get User Me
    print("Fetching /users/me...")
    try:
        resp = requests.get(f"{BASE_URL}/users/me", headers=headers)
        if resp.status_code != 200:
            print(f"Users/Me failed: {resp.status_code} {resp.text}")
        else:
            print("Users/Me success.")
            print(resp.json())
    except Exception as e:
        print(f"Users/Me exception: {e}")

    # 3. Get Company Me
    print("Fetching /companies/me...", flush=True)
    try:
        resp = requests.get(f"{BASE_URL}/companies/me", headers=headers)
        print(f"Companies/Me Status: {resp.status_code}", flush=True)
        print(f"Companies/Me Body: {resp.text}", flush=True)
        
        if resp.status_code != 200:
            print("Companies/Me failed.", flush=True)
        else:
            print("Companies/Me success.", flush=True)
    except Exception as e:
        print(f"Companies/Me exception: {e}", flush=True)

if __name__ == "__main__":
    test_flow()
