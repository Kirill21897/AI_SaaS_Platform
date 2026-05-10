from typing import List, Dict, Any
from app.models.profile import Profile
from app.models.track import Track
from app.services import qdrant_service

class RecommendationEngine:
    def __init__(self, db_session):
        self.db = db_session

    def recommend(self, profile: Profile, filters: Dict[str, Any] = None, user_query: str = None) -> List[Dict[str, Any]]:
        """
        Main deterministic recommendation pipeline.
        1. Semantic Search
        2. Hard Filters
        3. Skill Scoring
        4. Final Ranking
        """
        filters = filters or {}
        
        # 1. Generate query for semantic search
        # Combine profile data and actual user query for better contextual search
        query_text = f"Specialty: {profile.specialty}. "
        query_text += f"About: {profile.about}. "
        query_text += f"Skills: {', '.join(profile.skills)}. "
        
        if user_query:
            query_text += f"User Request: {user_query}. "
        
        # Get top 15 semantic matches from Qdrant
        semantic_results = qdrant_service.search_tracks(query_text, limit=15)
        
        scored_tracks = []
        
        for result in semantic_results:
            track_id = result.id
            semantic_score = result.score
            track_payload = result.payload
            
            # 2. Hard Filters
            if not self._passes_hard_filters(track_payload, filters):
                continue
                
            # Fetch full track from DB to get skill weights
            track = self.db.query(Track).filter(Track.id == track_id).first()
            if not track:
                continue
                
            # 3. Skill Scoring
            skill_score = self._calculate_skill_score(profile.skills, track.required_skills)
            
            # 4. Final Ranking Formula
            # 40% Semantic Similarity + 60% Skill Match (Giving more weight to skills for precise matching)
            final_score = (semantic_score * 0.40) + (skill_score * 0.60)
            
            # Only recommend if there is a minimum threshold of relevance
            if final_score < 0.2:
                continue
                
            scored_tracks.append({
                "track": track,
                "semantic_score": semantic_score,
                "skill_score": skill_score,
                "final_score": final_score,
                "explanation_data": {
                    "matched_skills": [s for s in profile.skills if s.lower() in [rs.lower() for rs in track.required_skills.keys()]],
                    "format_match": track.format == filters.get('format') if filters.get('format') else True
                }
            })
            
        # Sort by final score descending
        scored_tracks.sort(key=lambda x: x["final_score"], reverse=True)
        
        # Format the description so LLM doesn't see huge texts that eat context
        # and cause generation delays or cutoffs
        for st in scored_tracks:
            st["track"].description = st["track"].description[:100] + "..." if st["track"].description and len(st["track"].description) > 100 else st["track"].description
            
        return scored_tracks[:3] # Return top 3 most relevant instead of 5 to not overwhelm the LLM
        
    def _passes_hard_filters(self, track_payload: Dict, filters: Dict) -> bool:
        if not track_payload.get("is_active"):
            return False
            
        if filters.get("format") and track_payload.get("format"):
            if filters["format"].lower() != track_payload["format"].lower():
                return False
                
        if filters.get("region") and track_payload.get("region"):
            # Simple exact match for MVP, can be expanded to geosearch
            if filters["region"].lower() != track_payload["region"].lower():
                return False
                
        return True

    def _calculate_skill_score(self, user_skills: List[str], required_skills: Dict[str, float]) -> float:
        if not required_skills or not user_skills:
            return 0.0
            
        user_skills_lower = [s.lower() for s in user_skills]
        score = 0.0
        max_possible_score = sum(required_skills.values())
        
        if max_possible_score == 0:
            return 1.0 # If no weights defined, assume full match
            
        for req_skill, weight in required_skills.items():
            if req_skill.lower() in user_skills_lower:
                score += weight
                
        # Normalize to 0.0 - 1.0
        return min(score / max_possible_score, 1.0)
