import secrets
import string
import hashlib

def generate_api_key(length: int = 32) -> str:
    """
    Default length of 32.
    Max length of 32.
    """

    if length > 32:
        return "Length must be 32 or less"
        
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))

def encrypt_api_key(plain_key: str) -> str:
    return hashlib.sha256(plain_key.encode()).hexdigest()