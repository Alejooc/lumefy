from app.core.security import get_password_hash

try:
    hash = get_password_hash("test")
    print(f"Hash success: {hash}")
except Exception as e:
    print(f"Hash failed: {e}")
