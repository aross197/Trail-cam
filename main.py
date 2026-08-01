"""
AREA 51 TACTICAL - Trail Camera Server
3 Users (Bob, Mark, Rosco) + Chat + Compare + Graphs + Map Locations
"""

import uuid
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form, Depends, status
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime,
    BigInteger, Float, Boolean, ForeignKey, Text, func
)
from sqlalchemy.orm import sessionmaker, declarative_base, relationship

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)
CAMERA_INBOX = BASE_DIR / "inbox"
CAMERA_INBOX.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{BASE_DIR / 'media.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".heic",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv",
}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "change-this-to-a-long-random-secret-key-please"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# ---------------------------------------------------------------------------
# Database Models
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    email_notifications = Column(Boolean, default=True)
    notify_on_new_media = Column(Boolean, default=True)
    timezone = Column(String, default="UTC")
    theme = Column(String, default="dark")
    camera_name = Column(String, nullable=True)

    smtp_host = Column(String, nullable=True)
    smtp_port = Column(Integer, default=587)
    smtp_user = Column(String, nullable=True)
    smtp_password = Column(String, nullable=True)
    smtp_from = Column(String, nullable=True)

    media_files = relationship("MediaFile", back_populates="owner")


class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    stored_name = Column(String, unique=True, nullable=False)
    original_name = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(BigInteger, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    detected = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    age = Column(String, nullable=True)
    weight_live = Column(String, nullable=True)
    weight_dressed = Column(String, nullable=True)

    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="media_files")


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null = group
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    media_id = Column(Integer, ForeignKey("media_files.id"), nullable=True)


class CameraLocation(Base):
    __tablename__ = "camera_locations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Auth Helpers
# ---------------------------------------------------------------------------
def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if user is None:
            raise credentials_exception
        return user
    finally:
        db.close()

def send_email(user: User, subject: str, body: str):
    if not user.smtp_host or not user.smtp_user or not user.smtp_password:
        return False
    try:
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = user.smtp_from or user.smtp_user
        msg["To"] = user.email
        with smtplib.SMTP(user.smtp_host, user.smtp_port or 587) as server:
            server.starttls()
            server.login(user.smtp_user, user.smtp_password)
            server.send_message(msg)
        return True
    except Exception:
        return False

def create_default_users():
    db = SessionLocal()
    try:
        defaults = [
            {"username": "bob",   "email": "bob@trailcam.local",   "full_name": "Bob",   "password": "bob123"},
            {"username": "mark",  "email": "mark@trailcam.local",  "full_name": "Mark",  "password": "mark123"},
            {"username": "rosco", "email": "rosco@trailcam.local", "full_name": "Rosco", "password": "rosco123"},
        ]
        for u in defaults:
            if not db.query(User).filter(User.username == u["username"]).first():
                db.add(User(
                    username=u["username"],
                    email=u["email"],
                    full_name=u["full_name"],
                    hashed_password=get_password_hash(u["password"]),
                ))
        db.commit()
    finally:
        db.close()

create_default_users()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class UserCreate(BaseModel):
    email: EmailStr
    username: str
    password: str
    full_name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: str
    username: str
    full_name: Optional[str]
    email_notifications: bool
    notify_on_new_media: bool
    timezone: str
    theme: str
    camera_name: Optional[str]
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email_notifications: Optional[bool] = None
    notify_on_new_media: Optional[bool] = None
    timezone: Optional[str] = None
    theme: Optional[str] = None
    camera_name: Optional[str] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None
    smtp_user: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_from: Optional[str] = None

class Token(BaseModel):
    access_token: str
    token_type: str

class MediaOut(BaseModel):
    id: int
    original_name: str
    content_type: str
    size: int
    uploaded_at: datetime
    url: str
    detected: Optional[str] = None
    confidence: Optional[float] = None
    age: Optional[str] = None
    weight_live: Optional[str] = None
    weight_dressed: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
