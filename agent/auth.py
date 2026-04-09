"""Authentication module — signup, login, JWT, password hashing, Fernet encryption."""

import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, EmailStr, field_validator
from sqlalchemy.orm import Session

from agent.database import User, get_db

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24


def _get_jwt_secret() -> str:
    """Return the JWT secret, reading from the environment on each call.

    This lazy resolution avoids the need for ``load_dotenv()`` to run before
    this module is imported.  A ``RuntimeError`` is raised when the variable is
    missing and ``TESTING`` is not ``'1'``.
    """
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        if os.getenv("TESTING") == "1":
            return "test-secret-key"
        raise RuntimeError(
            "JWT_SECRET_KEY environment variable is not set. "
            "Set it to a strong random string before starting the application."
        )
    return secret


# Keep a module-level alias so existing test code that does
# ``from agent.auth import JWT_SECRET_KEY`` continues to work.
# At *import time* the env var may or may not be set; the property
# is only meaningful after dotenv has loaded or TESTING=1 is set.
JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY") or "test-secret-key"

# Fernet key for encrypting Luma credentials.
# Generate once via: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# Store in env var FERNET_KEY. If not set, derive a deterministic key from JWT_SECRET_KEY (dev only).
_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    """Return (and cache) a Fernet instance, lazily initialised."""
    global _fernet  # noqa: PLW0603
    if _fernet is not None:
        return _fernet
    raw_key = os.getenv("FERNET_KEY")
    if raw_key:
        _fernet = Fernet(raw_key.encode())
    else:
        import base64
        import hashlib
        _derived = base64.urlsafe_b64encode(
            hashlib.sha256(_get_jwt_secret().encode()).digest()
        )
        _fernet = Fernet(_derived)
    return _fernet

# ---------------------------------------------------------------------------
# Security scheme
# ---------------------------------------------------------------------------

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class SignupRequest(BaseModel):
    name: str
    email: str
    password: str
    linkedin_url: str | None = None
    job_title: str | None = None
    company: str | None = None
    phone: str | None = None
    twitter_x: str | None = None
    luma_email: str | None = None
    luma_password: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name is required")
        return v.strip()

    @field_validator("email")
    @classmethod
    def email_valid(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Email is required")
        v = v.strip().lower()
        if not _EMAIL_RE.match(v):
            raise ValueError("Invalid email format")
        return v

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    linkedin_url: str | None = None
    job_title: str | None = None
    company: str | None = None
    phone: str | None = None
    twitter_x: str | None = None
    luma_email: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def hash_password(password: str) -> str:
    """Hash a plain-text password with bcrypt."""
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Check a plain-text password against a bcrypt hash."""
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def encrypt_luma_password(plain: str) -> str:
    """Encrypt a Luma password with Fernet."""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_luma_password(encrypted: str) -> str:
    """Decrypt a Fernet-encrypted Luma password."""
    return _get_fernet().decrypt(encrypted.encode("utf-8")).decode("utf-8")


def create_access_token(user_id: int) -> str:
    """Create a JWT token with 24-hour expiry."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(hours=JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency — extract and validate JWT, return the User."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = credentials.credentials
    try:
        payload = jwt.decode(token, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        user_id = int(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    """Register a new user."""
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        linkedin_url=data.linkedin_url,
        job_title=data.job_title,
        company=data.company,
        phone=data.phone,
        twitter_x=data.twitter_x,
        luma_email=data.luma_email,
        luma_password_encrypted=(
            encrypt_luma_password(data.luma_password) if data.luma_password else None
        ),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return a JWT token."""
    user = db.query(User).filter(User.email == data.email.strip().lower()).first()
    if user is None or not verify_password(data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    token = create_access_token(user.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)):
    """Return the current user's profile (requires valid JWT)."""
    return current_user
