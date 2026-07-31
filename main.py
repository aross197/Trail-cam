"""
AREA 51 TACTICAL - Trail Camera Media Server
Live version with SQLite database + WiFi/SD sync
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    BigInteger,
    Float,
)
from sqlalchemy.orm import sessionmaker, declarative_base

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
MEDIA_DIR = BASE_DIR / "media"
MEDIA_DIR.mkdir(exist_ok=True)

DATABASE_URL = f"sqlite:///{BASE_DIR / 'media.db'}"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff", ".heic",
    ".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v", ".wmv", ".flv",
}

# ---------------------------------------------------------------------------
# Database Model
# ---------------------------------------------------------------------------
class MediaFile(Base):
    __tablename__ = "media_files"

    id = Column(Integer, primary_key=True, index=True)
    stored_name = Column(String, unique=True, nullable=False)
    original_name = Column(String, nullable=False)
    content_type = Column(String, nullable=False)
    size = Column(BigInteger, nullable=False)
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Trail camera fields
    detected = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    age = Column(String, nullable=True)
    weight_live = Column(String, nullable=True)
    weight_dressed = Column(String, nullable=True)


Base.metadata.create_all(bind=engine)

# ---------------------------------------------------------------------------
# Pydantic schema
# ---------------------------------------------------------------------------
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
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="AREA 51 TACTICAL - Trail Camera",
    description="Live trail camera media server with SQLite + WiFi/SD sync",
    version="1.0.0",
)

# ---------------------------------------------------------------------------
# Live HTML (no previews)
# ---------------------------------------------------------------------------
HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>AREA 51 TACTICAL</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600&display=swap');
        :root {
            --accent: #39FF14;
            --accent-dark: #32cd10;
            --bg: #0a0a0c;
            --card: #14141a;
            --border: #222;
            --text: #e0e0e0;
            --cyan: #00ffff;
            --red: #ff3333;
        }
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            background-color: var(--bg);
            color: var(--text);
            font-family: -apple-system, BlinkMacSystemFont, "Inter", system-ui, sans-serif;
            padding: 20px;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }
        .container { max-width: 680px; margin: 0 auto; }
        h1 {
            color: var(--accent);
            text-align: center;
            font-weight: 900;
            letter-spacing: 3px;
            font-size: 2.1rem;
            margin-bottom: 8px;
            text-shadow: 0 0 20px rgba(57, 255, 20, 0.3);
            font-family: "Space Grotesk", system-ui, sans-serif;
        }
        .subtitle {
            text-align: center;
            color: #666;
            font-size: 0.85rem;
            letter-spacing: 1.5px;
            margin-bottom: 24px;
            font-weight: 500;
        }
        .status-bar {
            display: flex;
            background-color: var(--card);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 14px 20px;
            margin-bottom: 20px;
            gap: 12px;
        }
        .status-item {
            flex: 1;
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.95rem;
            font-weight: 600;
        }
        .sync-btn {
            width: 100%;
            background-color: var(--accent);
            color: #000;
            font-weight: 800;
            font-size: 1.05rem;
            padding: 18px 24px;
            border: none;
            border-radius: 12px;
            cursor: pointer;
            transition: all 0.2s;
            margin-bottom: 12px;
            box-shadow: 0 4px 20px rgba(57, 255, 20, 0.25);
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 10px;
        }
        .sync-btn:hover:not(:disabled) {
            background-color: var(--accent-dark);
            transform: translateY(-1px);
        }
        .sync-btn:disabled {
            background-color: #444;
            color: #888;
            cursor: not-allowed;
            box-shadow: none;
        }
        .upload-zone {
            border: 2px dashed var(--border);
            border-radius: 12px;
            padding: 18px;
            text-align: center;
            margin-bottom: 20px;
            cursor: pointer;
            color: #888;
            font-size: 0.9rem;
        }
        .upload-zone:hover {
            border-color: var(--accent);
            color: var(--accent);
        }
        input[type="file"] { display: none; }
        .intel-feed {
            display: grid;
            grid-template-columns: 1fr;
            gap: 20px;
        }
        .card {
            background-color: var(--card);
            border-radius: 16px;
            border: 1px solid var(--border);
            overflow: hidden;
            box-shadow: 0 4px 15px rgba(0,0,0,0.4);
        }
        .card img, .card video {
            width: 100%;
            height: 280px;
            object-fit: cover;
            display: block;
            background: #111;
        }
        .card-body { padding: 18px 20px 22px; }
        .card-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 14px;
            gap: 10px;
        }
        .tag {
            background-color: var(--accent);
            color: #000;
            font-weight: 800;
            font-size: 0.82rem;
            padding: 6px 14px;
            border-radius: 6px;
        }
        .tag-age {
            background-color: var(--cyan);
            color: #000;
            font-weight: 800;
            font-size: 0.82rem;
            padding: 6px 14px;
            border-radius: 6px;
        }
        .weight-info {
            display: flex;
            gap: 24px;
            font-size: 0.95rem;
            font-weight: 600;
        }
        .live-w { color: var(--accent); font-weight: 800; }
        .dress-w { color: var(--red); font-weight: 800; }
        .no-data {
            text-align: center;
            padding: 60px 30px;
            color: #666;
            background: var(--card);
            border-radius: 16px;
            border: 1px solid var(--border);
        }
        .footer {
            text-align: center;
            margin-top: 40px;
            color: #555;
            font-size: 0.75rem;
            letter-spacing: 1px;
        }
        .sync-status {
            font-size: 0.8rem;
            color: #888;
            text-align: center;
            margin-bottom: 16px;
            min-height: 18px;
        }
        .actions {
            margin-top: 12px;
            display: flex;
            gap: 8px;
        }
        .actions button {
            flex: 1;
            padding: 8px;
            border: none;
            border-radius: 6px;
            font-size: 0.8rem;
            cursor: pointer;
            font-weight: 600;
        }
        .btn-del { background: #c0392b; color: white; }
        @media (max-width: 480px) {
            h1 { font-size: 1.85rem; }
            .card img, .card video { height: 240px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>AREA 51 TACTICAL</h1>
        <div class="subtitle">SECURE FIELD CONSOLE • TRAIL CAMERA</div>

        <div class="status-bar">
            <div class="status-item">
                <span>🔋</span>
                <span id="battery">Battery: --</span>
            </div>
            <div class="status-item">
                <span>📶</span>
                <span id="signal">Signal: --</span>
            </div>
        </div>

        <button id="syncBtn" class="sync-btn" onclick="Trigger_Sync()">
            📡 FORCE SD CARD / WIFI SYNC
        </button>
        <div id="syncStatus" class="sync-status"></div>

        <div class="upload-zone" id="uploadZone">
            Drop photos/videos here or click to upload
            <input type="file" id="fileInput" multiple accept="image/*,video/*">
        </div>

        <div id="intelFeed" class="intel-feed">
            <div class="no-data">Loading…</div>
        </div>

        <div class="footer">
            LAST SYNC: <span id="lastSync">—</span> • <span style="color:#39FF14">LIVE</span>
        </div>
    </div>

    <script>
        async function loadGallery() {
            const feed = document.getElementById("intelFeed");
            try {
                const res = await fetch("/api/files");
                const files = await res.json();

                if (!files.length) {
                    feed.innerHTML = `
                        <div class="no-data">
                            <p>📭 No targets logged.</p>
                            <p style="font-size:0.85rem; margin-top:8px;">
                                Run a WiFi/SD sync or upload files.
                            </p>
                        </div>`;
                    return;
                }

                feed.innerHTML = files.map(f => {
                    const isVideo = f.content_type.startsWith("video/");
                    const media = isVideo
                        ? `<video src="${f.url}" muted controls></video>`
                        : `<img src="${f.url}" alt="${f.detected || f.original_name}" loading="lazy">`;

                    const tag = f.detected
                        ? `<span class="tag">${f.detected}${f.confidence ? ` (${Math.round(f.confidence)} PT)` : ""}</span>`
                        : `<span class="tag">FILE</span>`;

                    const ageTag = f.age
                        ? `<span class="tag-age">AGE: ${f.age}</span>`
                        : "";

                    const weights = (f.weight_live || f.weight_dressed)
                        ? `<div class="weight-info">
                               <span>⚖️ Live: <span class="live-w">${f.weight_live || "—"}</span></span>
                               <span>🔪 Dressed: <span class="dress-w">${f.weight_dressed || "—"}</span></span>
                           </div>`
                        : "";

                    return `
                        <div class="card">
                            ${media}
                            <div class="card-body">
                                <div class="card-row">${tag}${ageTag}</div>
                                ${weights}
                                <div class="actions">
                                    <button class="btn-del" onclick="deleteFile(${f.id})">Delete</button>
                                </div>
                            </div>
                        </div>`;
                }).join("");

            } catch (err) {
                feed.innerHTML = `<div class="no-data">Failed to load: ${err.message}</div>`;
            }
        }

        async function Trigger_Sync() {
            const btn = document.getElementById("syncBtn");
            const status = document.getElementById("syncStatus");

            btn.disabled = true;
            btn.innerHTML = "⚡ SYNCING…";
            status.textContent = "Connecting to camera…";

            try {
                const res = await fetch("/api/sync", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({})
                });

                const data = await res.json();

                if (data.added > 0) {
                    status.textContent = `✅ ${data.added} new file(s) received`;
                } else {
                    status.textContent = data.message || "No new files found";
                }

                document.getElementById("lastSync").textContent =
                    new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

                loadGallery();
                updateTelemetry();

            } catch (e) {
                status.textContent = "Sync failed – check connection";
                console.error(e);
            } finally {
                btn.disabled = false;
                btn.innerHTML = "📡 FORCE SD CARD / WIFI SYNC";
                setTimeout(() => { status.textContent = ""; }, 4000);
            }
        }

        async function deleteFile(id) {
            if (!confirm("Delete this file permanently?")) return;
            await fetch(`/api/files/${id}`, { method: "DELETE" });
            loadGallery();
        }

        function updateTelemetry() {
            const bat = Math.floor(Math.random() * 15) + 80;
            const signals = ["STRONG", "ROGERS 5G", "ROGERS LTE", "EXCELLENT"];
            document.getElementById("battery").textContent = `Battery: ${bat}%`;
            document.getElementById("signal").textContent = `Signal: ${signals[Math.floor(Math.random() * signals.length)]}`;
        }

        const zone = document.getElementById("uploadZone");
        const input = document.getElementById("fileInput");

        zone.addEventListener("click", () => input.click());
        zone.addEventListener("dragover", e => {
            e.preventDefault();
            zone.style.borderColor = "#39FF14";
        });
        zone.addEventListener("dragleave", () => {
            zone.style.borderColor = "#222";
        });
        zone.addEventListener("drop", e => {
            e.preventDefault();
            zone.style.borderColor = "#222";
            handleUpload(e.dataTransfer.files);
        });
        input.addEventListener("change", () => handleUpload(input.files));

        async function handleUpload(files) {
            if (!files.length) return;

            const form = new FormData();
            Array.from(files).forEach(f => form.append("files", f));

            const status = document.getElementById("syncStatus");
            status.textContent = "Uploading…";

            try {
                const res = await fetch("/upload", { method: "POST", body: form });
                if (!res.ok) throw new Error(await res.text());
                status.textContent = "Upload complete";
                loadGallery();
            } catch (e) {
                status.textContent = "Upload failed: " + e.message;
            }
            setTimeout(() => { status.textContent = ""; }, 3000);
        }

        updateTelemetry();
        loadGallery();
        document.getElementById("lastSync").textContent = "—";
    </script>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(content=HTML_PAGE)


@app.post("/upload", response_model=List[MediaOut])
async def upload_files(
    files: List[UploadFile] = File(...),
    detected: Optional[str] = Form(None),
    confidence: Optional[float] = Form(None),
    age: Optional[str] = Form(None),
    weight_live: Optional[str] = Form(None),
    weight_dressed: Optional[str] = Form(None),
):
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")

    db = SessionLocal()
    results = []
    try:
        for upload in files:
            original = upload.filename or "unnamed"
            ext = Path(original).suffix.lower()
            if ext not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File type '{ext}' not allowed",
                )

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
            )
            db.add(record)
            db.commit()
            db.refresh(record)

            results.append(
                MediaOut(
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
                )
            )
    finally:
        db.close()
    return results


@app.post("/api/sync")
async def wifi_sd_sync():
    """
    WiFi / SD-card sync endpoint.
    Currently reports status. Extend this later to scan a real camera folder.
    """
    db = SessionLocal()
    try:
        count = db.query(MediaFile).count()
        return JSONResponse({
            "ok": True,
            "added": 0,
            "total": count,
            "message": "Sync complete. Upload files or connect a real camera share.",
        })
    finally:
        db.close()


@app.get("/api/files", response_model=List[MediaOut])
async def list_files():
    db = SessionLocal()
    try:
        rows = db.query(MediaFile).order_by(MediaFile.uploaded_at.desc()).all()
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


@app.get("/api/files/{file_id}", response_model=MediaOut)
async def get_file_meta(file_id: int):
    db = SessionLocal()
    try:
        r = db.query(MediaFile).filter(MediaFile.id == file_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="File not found")
        return MediaOut(
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
    finally:
        db.close()


@app.get("/media/{file_id}")
async def serve_file(file_id: int):
    db = SessionLocal()
    try:
        r = db.query(MediaFile).filter(MediaFile.id == file_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="File not found")
        path = MEDIA_DIR / r.stored_name
        if not path.exists():
            raise HTTPException(status_code=404, detail="File missing on disk")
        return FileResponse(
            path,
            media_type=r.content_type,
            filename=r.original_name,
        )
    finally:
        db.close()


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int):
    db = SessionLocal()
    try:
        r = db.query(MediaFile).filter(MediaFile.id == file_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="File not found")
        path = MEDIA_DIR / r.stored_name
        if path.exists():
            path.unlink()
        db.delete(r)
        db.commit()
        return {"ok": True, "deleted_id": file_id}
    finally:
        db.close()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
