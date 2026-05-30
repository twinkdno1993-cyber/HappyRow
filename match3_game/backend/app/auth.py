from passlib.context import CryptContext
from passlib.hash import sha256_crypt
from jose import jwt
from datetime import datetime, timedelta
import random
import os
from dotenv import load_dotenv

load_dotenv()

pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def hash_password(password: str) -> str:
    return sha256_crypt.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return sha256_crypt.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except:
        return None


def generate_verification_code() -> str:
    return f"{random.randint(100000, 999999)}"