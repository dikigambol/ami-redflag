import os
import requests
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dotenv import load_dotenv
import jwt
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database import User, get_user_by_id

load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "").strip()
SECRET_KEY = os.getenv("SECRET_KEY", "ami_redflag_jwt_secret_key_super_secure_2026")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 30

security = HTTPBearer(auto_error=False)

def verify_google_token(token_str: str) -> Dict[str, Any]:
    """
    Verifies a Google ID Token using google-auth library with fallback
    to Google tokeninfo endpoint.
    """
    # 1. Try google-auth official verification
    try:
        idinfo = id_token.verify_oauth2_token(
            token_str,
            google_requests.Request(),
            GOOGLE_CLIENT_ID
        )
        return idinfo
    except Exception as e:
        print(f"google-auth verify failed ({e}), trying tokeninfo fallback...")

    # 2. Fallback to tokeninfo endpoint
    try:
        resp = requests.get(
            f"https://oauth2.googleapis.com/tokeninfo?id_token={token_str}",
            timeout=5
        )
        if resp.status_code == 200:
            data = resp.json()
            if GOOGLE_CLIENT_ID and data.get("aud") != GOOGLE_CLIENT_ID:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token audience"
                )
            return data
    except Exception as e2:
        print(f"Fallback tokeninfo error: {e2}")

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token Google tidak valid atau telah kedaluwarsa."
    )

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_current_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> User:
    if not auth or not auth.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Silakan login dengan akun Google terlebih dahulu untuk bermain."
        )
    token = auth.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Sesi tidak valid."
            )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesi telah kedaluwarsa. Silakan login kembali."
        )

    user = get_user_by_id(str(user_id))
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Pengguna tidak ditemukan."
        )
    return user

def get_optional_user(
    auth: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    if not auth or not auth.credentials:
        return None
    try:
        payload = jwt.decode(auth.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if user_id:
            return get_user_by_id(str(user_id))
    except Exception:
        return None
    return None

def check_user_quota(user: User):
    """
    Checks if user still has trials left (max 3 by default).
    Raises 403 if exhausted.
    """
    max_trials = user.max_trials if user.max_trials is not None else 3
    used = user.trial_used if user.trial_used is not None else 0
    if used >= max_trials:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Batas maksimal percobaan bermain ({max_trials}x) Anda telah habis."
        )
