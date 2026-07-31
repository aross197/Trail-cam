# AREA 51 TACTICAL – Trail Camera Server

Live trail camera media server with SQLite database and WiFi/SD-card sync.

## Features

- Dark tactical web UI (AREA 51 TACTICAL)
- Upload photos & videos
- SQLite database for file metadata + detection data
- WiFi / SD-card style sync endpoint
- Files stored on disk in `media/` folder
- Delete files from the UI

## Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/YOUR-USERNAME/trail-camera.git
cd trail-camera

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
