import secrets
import string
import hashlib

def generate_api_key(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def encrypt_api_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()