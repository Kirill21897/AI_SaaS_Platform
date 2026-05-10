from typing import List, Dict, Any

class RAGTool:
    def __init__(self, db, rec_engine):
        self.db = db
        self.rec_engine = rec_engine

    def search_tracks(
        self,
        query: str,
        filters: Dict[str, Any] = None,
        limit: int = 5,
        offset: int = 0,
    ) -> List[Dict]:
        """Search tracks by meaning/semantics"""
        offset = max(int(offset or 0), 0)
        limit = max(int(limit or 5), 1)
        total = offset + limit
        results = self.rec_engine.explore(user_query=query, filters=filters, limit=total)
        formatted = [self._format_track_result(r) for r in results]
        return formatted[offset : offset + limit]

    def recommend_tracks(
        self,
        profile,
        user_query: str = None,
        limit: int = 3,
        offset: int = 0,
        filters: Dict[str, Any] = None,
    ) -> List[Dict]:
        """Recommend tracks based on user profile skills"""
        offset = max(int(offset or 0), 0)
        limit = max(int(limit or 3), 1)
        total = offset + limit
        results = self.rec_engine.recommend(profile=profile, user_query=user_query, filters=filters, limit=total)
        formatted = [self._format_track_result(r) for r in results]
        return formatted[offset : offset + limit]
        
    def _format_track_result(self, item: Dict) -> Dict:
        t = item["track"]
        return {
            "id": t.id,
            "title": t.title,
            "specialization": t.specialization,
            "region": t.region,
            "format": t.format,
            "match_score": int(item.get("final_score", 0) * 100),
            "matched_skills": item.get("explanation_data", {}).get("matched_skills", [])
        }
