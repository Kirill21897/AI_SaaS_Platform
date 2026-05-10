import sys
import os

# Add path so we can import from app
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.track import Track
from app.services import qdrant_service

def index_all_tracks():
    print("Initializing Qdrant collections...")
    qdrant_service.init_collections()
    
    db = SessionLocal()
    try:
        tracks = db.query(Track).filter(Track.is_active == True).all()
        print(f"Found {len(tracks)} active tracks to index.")
        
        for track in tracks:
            print(f"Indexing track [{track.id}]: {track.title}...")
            qdrant_service.index_track(track)
            
        print("✅ All tracks successfully indexed in Qdrant!")
    except Exception as e:
        print(f"❌ Error indexing tracks: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    index_all_tracks()
