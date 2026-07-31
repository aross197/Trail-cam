"""
AREA 51 TACTICAL - Trail Camera Server
With Registration, Login, Personal Settings & Email
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
    BigInteger, Float, Boolean, ForeignKey, Text
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

# Auth settings
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = "change-this-to-a-long-random-secret-key-please"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
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

    # Personal settings
    email_notifications = Column(Boolean, default=True)
    notify_on_new_media = Column(Boolean, default=True)
    timezone = Column(String, default="UTC")
    theme = Column(String, default="dark")
    camera_name = Column(String, nullable=True)

    # SMTP / Email settings
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

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    owner = relationship("User", back_populates="media_files")


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
    """Send email using the user's own SMTP settings"""
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

# ---------------------------------------------------------------------------
# Pydantic Schemas
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

    class Config:
        from_attributes = True

# ---------------------------------------------------------------------------
# FastAPI App
# ---------------------------------------------------------------------------
app = FastAPI(title="AREA 51 TACTICAL", version="2.0.0")

# ---------------------------------------------------------------------------
# Auth Routes
# ---------------------------------------------------------------------------
@app.post("/register", response_model=UserOut)
def register(user: UserCreate):
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == user.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        if db.query(User).filter(User.username == user.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")

        db_user = User(
            email=user.email,
            username=user.username,
            hashed_password=get_password_hash(user.password),
            full_name=user.full_name,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        return db_user
    finally:
        db.close()

@app.post("/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends()):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == form_data.username).first()
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(status_code=400, detail="Incorrect username or password")
        access_token = create_access_token(data={"sub": user.username})
        return {"access_token": access_token, "token_type": "bearer"}
    finally:
        db.close()

@app.get("/me", response_model=UserOut)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@app.put("/me", response_model=UserOut)
async def update_settings(update: UserUpdate, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == current_user.id).first()
        for field, value in update.dict(exclude_unset=True).items():
            setattr(user, field, value)
        db.commit()
        db.refresh(user)
        return user
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Media Routes (protected)
# ---------------------------------------------------------------------------
@app.post("/upload", response_model=List[MediaOut])
async def upload_files(
    files: List[UploadFile] = File(...),
    detected: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    age: Optional[str] = Form(None),
    weight_live: Optional[str] = Form(None),
    weight_dressed: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
):
    db = SessionLocal()
    results = []
    try:
        for upload in files:
            original = upload.filename or "unnamed"
            ext = Path(original).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(status_code=400, detail=f"File type '{ext}' not allowed")

            stored_name = f"{uuid.uuid4().hex}{ext}"
            dest = MEDIA_DIR / stored_name
            content = await upload.read()
            with open(dest, "wb") as f:
                f.write(content)

            record = MediaFile(
                stored_name=stored_name,
                original_name=original,
                content_type=upload.content_type or "application/octet-stream",
                size=len(content),
                detected=detected,
                confidence=confidence,
                age=age,
                weight_live=weight_live,
                weight_dressed=weight_dressed,
                owner_id=current_user.id,
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            results.append(MediaOut(
                id=record.id,
                original_name=record.original_name,
                content_type=record.content_type,
                size=record.size,
                uploaded_at=record.uploaded_at,
                url=f"/media/{record.id}",
                detected=record.detected,
                confidence=record.confidence,
                age=record.age,
                weight_live=record.weight_live,
                weight_dressed=record.weight_dressed,
            ))

            # Send email notification if enabled
            if current_user.notify_on_new_media and current_user.email_notifications:
                send_email(
                    current_user,
                    "New Trail Camera Media",
                    f"New file uploaded: {original}"
                )
    finally:
        db.close()
    return results

@app.get("/api/files", response_model=List[MediaOut])
async def list_files(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        rows = db.query(MediaFile).filter(
            MediaFile.owner_id == current_user.id
        ).order_by(MediaFile.uploaded_at.desc()).all()
        return [
            MediaOut(
                id=r.id,
                original_name=r.original_name,
                content_type=r.content_type,
                size=r.size,
                uploaded_at=r.uploaded_at,
                url=f"/media/{r.id}",
                detected=r.detected,
                confidence=r.confidence,
                age=r.age,
                weight_live=r.weight_live,
                weight_dressed=r.weight_dressed,
            )
            for r in rows
        ]
    finally:
        db.close()

@app.get("/media/{file_id}")
async def serve_file(file_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        r = db.query(MediaFile).filter(
            MediaFile.id == file_id,
            MediaFile.owner_id == current_user.id
        ).first()
        if not r:
            raise HTTPException(status_code=404, detail="File not found")
        path = MEDIA_DIR / r.stored_name
        if not path.exists():
            raise HTTPException(status_code=404, detail="File missing on disk")
        return FileResponse(path, media_type=r.content_type, filename=r.original_name)
    finally:
        db.close()

@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int, current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    try:
        r = db.query(MediaFile).filter(
            MediaFile.id == file_id,
            MediaFile.owner_id == current_user.id
        ).first()
        if not r:
            raise HTTPException(status_code=404, detail="File not found")
        path = MEDIA_DIR / r.stored_name
        if path.exists():
            path.unlink()
        db.delete(r)
        db.commit()
        return {"ok": True}
    finally:
        db.close()

@app.post("/api/sync")
async def wifi_sd_sync(current_user: User = Depends(get_current_user)):
    db = SessionLocal()
    added = 0
    try:
        existing = {row.original_name for row in db.query(MediaFile.original_name).filter(MediaFile.owner_id == current_user.id).all()}
        for file_path in CAMERA_INBOX.iterdir():
            if not file_path.is_file():
                continue
            ext = file_path.suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                continue
            original_name = file_path.name
            if original_name in existing:
                continue
            try:
                content = file_path.read_bytes()
                stored_name = f"{uuid.uuid4().hex}{ext}"
                dest = MEDIA_DIR / stored_name
                with open(dest, "wb") as f:
                    f.write(content)

                content_type = "application/octet-stream"
                if ext in {".jpg", ".jpeg"}: content_type = "image/jpeg"
                elif ext == ".png": content_type = "image/png"
                elif ext in {".mp4", ".m4v"}: content_type = "video/mp4"
                elif ext == ".mov": content_type = "video/quicktime"

                record = MediaFile(
                    stored_name=stored_name,
                    original_name=original_name,
                    content_type=content_type,
                    size=len(content),
                    owner_id=current_user.id,
                )
                db.add(record)
                db.commit()
                added += 1
            except Exception:
                db.rollback()
        return {"ok": True, "added": added, "message": f"Imported {added} new file(s)."}
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Simple frontend placeholder (you can replace with full UI later)
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse("""
    <html>
    <head><title>AREA 51 TACTICAL</title></head>
    <body style="background:#0a0a0c;color:#e0e0e0;font-family:sans-serif;padding:40px;text-align:center;">
        <h1 style="color:#39FF14;">AREA 51 TACTICAL</h1>
        <p>Login system is active.</p>
        <p>Use /register and /token endpoints, or connect a frontend.</p>
        <p>API docs: <a href="/docs" style="color:#39FF14;">/docs</a></p>
    </body>
    </html>
    """)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
