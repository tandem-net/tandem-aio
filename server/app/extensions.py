import secrets
import string

from flask_redis import FlaskRedis
from flask_sqlalchemy import SQLAlchemy

redis_client = FlaskRedis()
db = SQLAlchemy()

# API KEY SLOP

def generate_api_key(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))