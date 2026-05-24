from typing import List, Dict, Any, Optional
from langchain_core.tools import StructuredTool

class AgenticRAGTools:
    def __init__(self, db, rec_engine, llm=None):
        self.db = db
        self.rec_engine = rec_engine
        self.llm = llm

    def search_tracks(self, query: str, limit: int = 5) -> List[Dict]:
        """Search for career tracks in the database based on a query."""
        results = self.rec_engine.explore(user_query=query, filters={}, limit=limit)
        return [self._format_track_result(r) for r in results]

    def filter_tracks(
        self,
        specialization: Optional[str] = None,
        format: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict]:
        """Filter tracks strictly by specialization, format, or region."""
        from app.models.track import Track
        query = self.db.query(Track).filter(Track.is_active == True)
        if specialization:
            query = query.filter(Track.specialization.ilike(f"%{specialization}%"))
        if format:
            query = query.filter(Track.format.ilike(f"%{format}%"))
        if region:
            query = query.filter(Track.region.ilike(f"%{region}%"))
        
        tracks = query.limit(limit).all()
        return [{
            "id": t.id,
            "title": t.title,
            "specialization": t.specialization,
            "region": t.region,
            "format": t.format,
            "skills": t.required_skills
        } for t in tracks]

    def fetch_track_details(self, track_id: int) -> Dict:
        """Fetch full track info and description by track ID."""
        from app.models.track import Track
        track = self.db.query(Track).filter(Track.id == track_id, Track.is_active == True).first()
        if not track:
            return {}
        return {
            "id": track.id,
            "title": track.title,
            "specialization": track.specialization,
            "region": track.region,
            "format": track.format,
            "description": track.description,
            "skills": track.required_skills
        }

    def get_tools(self) -> List[StructuredTool]:
        return [
            StructuredTool.from_function(
                func=self.search_tracks,
                name="search_tracks",
                description="Search for career or educational tracks using semantic search. Use this when the user describes what they want to learn or do."
            ),
            StructuredTool.from_function(
                func=self.filter_tracks,
                name="filter_tracks",
                description="Filter tracks strictly by specialization, format (e.g. Remote, Office, Hybrid), or region (e.g. Москва). Use this when the user asks for exact matches."
            ),
            StructuredTool.from_function(
                func=self.fetch_track_details,
                name="fetch_track_details",
                description="Fetch full details, description and required skills of a specific track by its ID."
            )
        ]

    def _format_track_result(self, item: Dict) -> Dict:
        t = item["track"]
        return {
            "id": t.id,
            "title": t.title,
            "specialization": t.specialization,
            "region": t.region,
            "format": t.format,
            "skills": t.required_skills,
            "match_score": item.get("final_score", 0)
        }

