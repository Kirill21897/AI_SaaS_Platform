from typing import List, Dict, Any
from app.models.profile import Profile
from app.models.track import Track
from app.services import qdrant_service
import re

class RecommendationEngine:
    def __init__(self, db_session):
        self.db = db_session

    def _detect_specialization(self, user_query: str | None) -> str | None:
        text = (user_query or "").lower()
        if not text.strip():
            return None

        keywords = [
            ("design", ["дизайн", "дизайнер", "ux", "ui", "ux/ui", "product design", "product designer", "graphic", "figma"]),
            ("frontend", ["frontend", "фронтенд", "front-end", "react", "next.js", "nextjs", "javascript", "typescript"]),
            ("backend", ["backend", "бэкенд", "back-end", "fastapi", "django", "api", "python backend"]),
            ("data", ["data", "data science", "datascience", "ml", "machine learning", "аналитик", "data analyst", "датасаенс", "дата саенс"]),
            ("devops", ["devops", "sre", "kubernetes", "k8s", "docker", "terraform", "linux"]),
        ]

        for canonical, variants in keywords:
            for v in variants:
                if v in text:
                    return canonical
        return None
    
    def detect_specialization(self, user_query: str | None) -> str | None:
        return self._detect_specialization(user_query)

    def explore(self, user_query: str | None, filters: Dict[str, Any] = None, limit: int = 7) -> List[Dict[str, Any]]:
        filters = filters or {}
        target_spec = self._detect_specialization(user_query)
        if target_spec:
            filters = {**filters, "specialization": target_spec}

        query_text = (user_query or "").strip()
        if not query_text:
            return []

        semantic_results = qdrant_service.search_tracks(query_text, limit=max(15, limit * 3))
        if not semantic_results:
            return self._fallback_explore(query_text=query_text, filters=filters, limit=limit)
        results: List[Dict[str, Any]] = []
        for result in semantic_results:
            track_id = result.id
            semantic_score = result.score
            track_payload = result.payload

            if not self._passes_hard_filters(track_payload, filters):
                continue

            track = self.db.query(Track).filter(Track.id == track_id).first()
            if not track:
                continue

            if semantic_score < 0.05:
                continue

            results.append(
                {
                    "track": track,
                    "semantic_score": semantic_score,
                    "skill_score": 0.0,
                    "final_score": semantic_score,
                    "explanation_data": {"matched_skills": []},
                }
            )

        results.sort(key=lambda x: x["final_score"], reverse=True)
        for st in results:
            st["track"].description = (
                st["track"].description[:100] + "..."
                if st["track"].description and len(st["track"].description) > 100
                else st["track"].description
            )
        return results[:limit]

    def recommend(
        self,
        profile: Profile,
        filters: Dict[str, Any] = None,
        user_query: str = None,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Main deterministic recommendation pipeline.
        1. Semantic Search
        2. Hard Filters
        3. Skill Scoring
        4. Final Ranking
        """
        filters = filters or {}

        target_spec = self._detect_specialization(user_query)
        if target_spec:
            filters = {**filters, "specialization": target_spec}
        
        # 1. Generate query for semantic search
        # Combine profile data and actual user query for better contextual search
        query_text = ""
        if user_query:
            query_text += f"User Request: {user_query}. "
        if target_spec:
            query_text += f"Target Specialization: {target_spec}. "

        profile_specialty = (profile.specialty or "").lower()
        if not target_spec or target_spec in profile_specialty:
            query_text += f"Specialty: {profile.specialty}. "
            query_text += f"About: {profile.about}. "
            query_text += f"Skills: {', '.join(profile.skills)}. "
        
        # Get top 15 semantic matches from Qdrant
        semantic_results = qdrant_service.search_tracks(query_text, limit=15)
        if not semantic_results:
            return self._fallback_recommend(profile=profile, filters=filters, limit=limit)
        
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
            
        return scored_tracks[: max(int(limit or 3), 1)]

    def _apply_sql_filters(self, query, filters: Dict[str, Any]):
        if filters.get("format"):
            query = query.filter(Track.format.ilike(f"%{filters['format']}%"))
        if filters.get("region"):
            query = query.filter(Track.region.ilike(f"%{filters['region']}%"))
        if filters.get("specialization"):
            requested = str(filters["specialization"]).lower()
            if requested == "design":
                query = query.filter(Track.specialization.ilike("%design%"))
            elif requested == "frontend":
                query = query.filter(Track.specialization.ilike("%front%"))
            elif requested == "backend":
                query = query.filter(Track.specialization.ilike("%back%"))
            elif requested == "data":
                query = query.filter(Track.specialization.ilike("%data%"))
            elif requested == "devops":
                query = query.filter(Track.specialization.ilike("%devops%"))
            else:
                query = query.filter(Track.specialization.ilike(f"%{filters['specialization']}%"))
        return query

    def _fallback_explore(self, query_text: str, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        tokens = [t for t in re.split(r"[\s,;:.!?/()\\[\]{}]+", query_text) if len(t) >= 3]
        q = self.db.query(Track).filter(Track.is_active == True)
        q = self._apply_sql_filters(q, filters)
        if tokens:
            from sqlalchemy import or_

            ors = []
            for t in tokens[:8]:
                like = f"%{t}%"
                ors.append(Track.title.ilike(like))
                ors.append(Track.description.ilike(like))
                ors.append(Track.specialization.ilike(like))
            q = q.filter(or_(*ors))
        tracks = q.order_by(Track.id.asc()).limit(max(int(limit or 7), 1)).all()
        return [
            {
                "track": t,
                "semantic_score": 0.0,
                "skill_score": 0.0,
                "final_score": 0.0,
                "explanation_data": {"matched_skills": []},
            }
            for t in tracks
        ]

    def _fallback_recommend(self, profile: Profile, filters: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
        q = self.db.query(Track).filter(Track.is_active == True)
        q = self._apply_sql_filters(q, filters)
        candidates = q.order_by(Track.id.asc()).limit(100).all()

        scored_tracks: List[Dict[str, Any]] = []
        user_skills = list(getattr(profile, "skills", []) or [])
        for t in candidates:
            skill_score = self._calculate_skill_score(user_skills, t.required_skills)
            matched = [s for s in user_skills if s.lower() in [rs.lower() for rs in (t.required_skills or {}).keys()]]
            final_score = skill_score
            if final_score <= 0:
                continue
            scored_tracks.append(
                {
                    "track": t,
                    "semantic_score": 0.0,
                    "skill_score": skill_score,
                    "final_score": final_score,
                    "explanation_data": {"matched_skills": matched, "format_match": True},
                }
            )

        scored_tracks.sort(key=lambda x: x["final_score"], reverse=True)
        for st in scored_tracks:
            st["track"].description = (
                st["track"].description[:100] + "..."
                if st["track"].description and len(st["track"].description) > 100
                else st["track"].description
            )
        return scored_tracks[: max(int(limit or 3), 1)]
        
    def _passes_hard_filters(self, track_payload: Dict, filters: Dict) -> bool:
        if not track_payload.get("is_active"):
            return False

        if filters.get("specialization") and track_payload.get("specialization"):
            requested = str(filters["specialization"]).lower()
            actual = str(track_payload["specialization"]).lower()
            if requested == "design":
                if not re.search(r"\b(design|designer|ux|ui)\b", actual):
                    return False
            elif requested == "frontend":
                if not re.search(r"\b(frontend|front-end|react|next)\b", actual):
                    return False
            elif requested == "backend":
                if not re.search(r"\b(backend|back-end|api)\b", actual):
                    return False
            elif requested == "data":
                if not re.search(r"\b(data|ml|machine learning|analyst|science)\b", actual):
                    return False
            elif requested == "devops":
                if not re.search(r"\b(devops|sre|kubernetes|k8s)\b", actual):
                    return False
            else:
                if requested not in actual:
                    return False
            
        if filters.get("format") and track_payload.get("format"):
            requested = str(filters["format"]).lower()
            actual = str(track_payload["format"]).lower()
            if requested not in actual:
                return False
                
        if filters.get("region") and track_payload.get("region"):
            # Simple exact match for MVP, can be expanded to geosearch
            requested = str(filters["region"]).lower()
            actual = str(track_payload["region"]).lower()
            if requested not in actual:
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
