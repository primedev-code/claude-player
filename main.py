import os
from tinytag import TinyTag 
from fastapi import FastAPI, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import init_db, SessionLocal, TrackModel

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")


templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


init_db()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/api/tracks")
def get_tracks(db: Session = Depends(get_db)):
    tracks = db.query(TrackModel).all()
    
    return [
        {
            "id": track.id,
            "title": track.title,
            "artist": track.artist,
            "src": track.src,
            "cover": track.cover
            
        }
        for track in tracks
    ]
    
@app.post("/api/tracks/scan")
def scan_audio_folder(db: Session = Depends(get_db)):
    audio_dir = "static/audio"
    files = [f for f in os.listdir(audio_dir) if f.endswith(".mp3")]
    
    added_count = 0
    for filename in files:
        file_path = f"/static/audio/{filename}"
        full_disk_path = os.path.join(audio_dir, filename)
        
        existing = db.query(TrackModel).filter(TrackModel.src == file_path).first()
        if not existing:
            title = None
            artist = None
            try:
                tag = TinyTag.get(full_disk_path)
                title = tag.title
                artist = tag.artist
            except Exception:
                pass
            
            clean_filename = filename.replace('.mp3', '')
            
            if not title or not artist:
                if "-" in clean_filename:
                    parts = clean_filename.split("-", 1)
                    artist = artist or parts[0].strip()
                    title = title or parts[1].strip()
                else:
                    title = title or clean_filename
                    artist = artist or "Неизвестный исполнитель"
            
            new_track = TrackModel(
                title=title,
                artist=artist,
                src=file_path,
                cover=None
            )
            db.add(new_track)
            added_count += 1
            
    db.commit()
    return {"status": "Сканирование завершено!", "добавлено_треков": added_count}