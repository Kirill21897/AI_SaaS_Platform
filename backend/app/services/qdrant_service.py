from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams, PointStruct
from app.core.config import settings
from app.services import embedding_service

# Initialize Qdrant client
# In qdrant-client >= 1.7.0, host and port are deprecated in favor of url or passing them separately if needed.
# For 1.17.1, we should pass url.
qdrant = QdrantClient(url=f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}")

def init_collections():
    """
    Creates the necessary collections in Qdrant if they don't exist.
    """
    collections = qdrant.get_collections().collections
    collection_names = [col.name for col in collections]
    
    vector_size = embedding_service.get_embedding_dimension()

    if settings.QDRANT_COLLECTION_TRACKS not in collection_names:
        print(f"Creating Qdrant collection: {settings.QDRANT_COLLECTION_TRACKS}")
        qdrant.create_collection(
            collection_name=settings.QDRANT_COLLECTION_TRACKS,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )
        return

    info = qdrant.get_collection(settings.QDRANT_COLLECTION_TRACKS)
    existing_size = info.config.params.vectors.size
    if existing_size != vector_size:
        if settings.QDRANT_RECREATE_COLLECTIONS:
            qdrant.delete_collection(collection_name=settings.QDRANT_COLLECTION_TRACKS)
            qdrant.create_collection(
                collection_name=settings.QDRANT_COLLECTION_TRACKS,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
            )
            return
        raise ValueError(
            f"Qdrant collection '{settings.QDRANT_COLLECTION_TRACKS}' vector size is {existing_size}, "
            f"but embedding size is {vector_size}. "
            f"Set QDRANT_RECREATE_COLLECTIONS=true and reindex, or align EMBEDDING_DIMENSION/model."
        )

def index_track(track):
    """
    Generates embedding for a track and saves it to Qdrant.
    """
    text_to_embed = embedding_service.create_track_text_for_embedding(track)
    vector = embedding_service.generate_embedding(text_to_embed)
    
    payload = {
        "track_id": track.id,
        "title": track.title,
        "specialization": track.specialization,
        "region": track.region,
        "format": track.format,
        "min_gpa": track.min_gpa,
        "is_active": track.is_active
    }
    
    qdrant.upsert(
        collection_name=settings.QDRANT_COLLECTION_TRACKS,
        points=[
            PointStruct(
                id=track.id,  # Use track DB ID as Qdrant point ID
                vector=vector,
                payload=payload
            )
        ]
    )
    return True

def search_tracks(query_text: str, limit: int = 15):
    """
    Semantic search for tracks.
    """
    global qdrant
    query_vector = embedding_service.generate_embedding(query_text)
    
    # Check if we got a fallback/mock vector due to API limits or errors
    # If the collection is empty or the vector API fails, we should handle it gracefully
    try:
        init_collections()
        collection_info = qdrant.get_collection(settings.QDRANT_COLLECTION_TRACKS)
        if (collection_info.points_count or 0) == 0:
            print("WARNING: Qdrant collection is empty. Run index_tracks.py first.")
            return []

        if hasattr(qdrant, "search"):
            return qdrant.search(
                collection_name=settings.QDRANT_COLLECTION_TRACKS,
                query_vector=query_vector,
                limit=limit
            )

        # Compatibility path for newer qdrant-client versions.
        query_response = qdrant.query_points(
            collection_name=settings.QDRANT_COLLECTION_TRACKS,
            query=query_vector,
            limit=limit
        )
        return query_response.points
    except Exception as e:
        print(f"Qdrant search error: {e}")
        return []
