import json
from typing import Dict, Any
from .state import RAGState
from .tools import AgenticRAGTools
from .utils import extract_first_json_object

class RAGNodes:
    def __init__(self, tools: AgenticRAGTools, llm):
        self.tools = tools
        self.llm = llm

    async def reasoning_node(self, state: RAGState) -> Dict:
        """
        Analyze user intent using LLM
        - Determine if searching, filtering, or clarifying
        - Decide breadth (many results) vs depth (detailed analysis)
        - Route to appropriate tools
        """
        user_message = state.get("user_message", "")
        filters = state.get("filters", {})
        
        prompt = (
            "Ты маршрутизатор запросов для системы подбора карьерных треков. "
            "Проанализируй запрос пользователя и определи намерение и стратегию поиска.\n\n"
            "Намерения (intent):\n"
            "- 'recommend': пользователь просит подобрать треки под его профиль.\n"
            "- 'search': пользователь ищет треки по конкретной теме или навыку.\n"
            "- 'filter': пользователь просто задает или меняет фильтры (например, 'только удаленка', 'в москве').\n"
            "- 'clarify': запрос непонятен или слишком короткий.\n\n"
            "Стратегии (strategy):\n"
            "- 'narrow': строгий поиск, нужно точное совпадение.\n"
            "- 'broad': широкий поиск, больше результатов.\n"
            "- 'exploratory': исследовательский поиск.\n\n"
            f"Запрос пользователя: {user_message}\n"
            f"Текущие фильтры: {filters}\n\n"
            "Верни ответ СТРОГО в формате JSON с ключами: 'intent', 'strategy', 'reasoning', 'extracted_filters' (если в запросе есть фильтры по городу, формату работы или специализации)."
        )
        
        raw_response = await self.llm.complete_chat([{"role": "user", "content": prompt}])
        json_str = extract_first_json_object(raw_response)
        
        try:
            parsed = json.loads(json_str) if json_str else {}
        except:
            parsed = {}
            
        intent = parsed.get("intent", "search")
        strategy = parsed.get("strategy", "broad")
        reasoning = parsed.get("reasoning", "")
        extracted_filters = parsed.get("extracted_filters", {})
        
        new_filters = state.get("filters", {}).copy()
        new_filters.update(extracted_filters)
        
        return {
            "intent": intent,
            "strategy": strategy,
            "reasoning": reasoning,
            "filters": new_filters
        }

    async def tool_executor_node(self, state: RAGState) -> Dict:
        """
        Execute selected tools
        """
        query = state.get("user_message", "")
        filters = state.get("filters", {})
        profile = state.get("profile", {})
        intent = state.get("intent", "search")
        
        limit = 15 if state.get("strategy") == "broad" else 5
        
        # 1. Search tracks
        raw_results = self.tools.search_tracks(query=query, limit=limit)
        
        # 2. Filter tracks
        filtered = self.tools.filter_tracks(
            raw_results, 
            specialization=filters.get("specialization"),
            format=filters.get("format"),
            region=filters.get("region")
        )
        
        # 3. Analyze skills
        skill_scores = {}
        user_skills = profile.get("skills", []) if profile else []
        
        for t in filtered:
            skills_data = t.get("skills") or {}
            if isinstance(skills_data, list):
                track_skills = {s: 1.0 for s in skills_data}
            else:
                track_skills = skills_data
                
            if user_skills and track_skills and intent == "recommend":
                analysis = self.tools.analyze_skill_match(user_skills, track_skills)
                skill_scores[t["id"]] = analysis["match_score"]
                t["matched_skills"] = analysis["matched_skills"]
                t["missing_skills"] = analysis["missing_skills"]
            else:
                skill_scores[t["id"]] = 0.5 
                
        return {
            "search_results": raw_results,
            "filtered_results": filtered,
            "skill_scores": skill_scores
        }

    async def evaluator_node(self, state: RAGState) -> Dict:
        """
        Score and rank results
        """
        filtered = state.get("filtered_results", [])
        skill_scores = state.get("skill_scores", {})
        strategy = state.get("strategy", "broad")
        intent = state.get("intent", "search")
        
        # Dynamic weights
        weight_semantic = 0.4
        weight_skill = 0.6
        if strategy == "narrow":
            weight_skill = 0.7
            weight_semantic = 0.3
        elif strategy == "broad":
            weight_semantic = 0.6
            weight_skill = 0.4
        if intent == "clarify":
            weight_semantic = 0.8
            weight_skill = 0.2
            
        ranked = []
        for t in filtered:
            semantic_score = float(t.get("match_score", 0)) / 100.0
            skill_score = skill_scores.get(t["id"], 0.5)
            
            final_score = (semantic_score * weight_semantic) + (skill_score * weight_skill)
            t["recommendation_score"] = final_score
            ranked.append(t)
            
        ranked.sort(key=lambda x: x["recommendation_score"], reverse=True)
        
        quality_score = ranked[0]["recommendation_score"] if ranked else 0.0
        needs_refinement = quality_score < 0.3 and intent != "clarify"
        
        return {
            "ranked_results": ranked,
            "quality_score": quality_score,
            "needs_refinement": needs_refinement
        }

    async def reflection_node(self, state: RAGState) -> Dict:
        """
        Optional reflective step
        """
        user_message = state.get("user_message", "")
        ranked = state.get("ranked_results", [])
        
        if not ranked or state.get("needs_refinement"):
            clarifying_question = await self.tools.clarify_intent(
                user_message, 
                "Система не нашла достаточно релевантных результатов по запросу."
            )
            return {
                "clarifying_question": clarifying_question,
                "intent": "clarify",
                "iteration_count": state.get("iteration_count", 0) + 1
            }
            
        return {"iteration_count": state.get("iteration_count", 0) + 1}

    async def response_builder_node(self, state: RAGState) -> Dict:
        """
        Format final response for user
        """
        ranked = state.get("ranked_results", [])
        intent = state.get("intent")
        
        if intent == "clarify" and state.get("clarifying_question"):
            return {
                "final_response": state.get("clarifying_question"),
                "metadata": {}
            }
            
        if not ranked:
            return {
                "final_response": "К сожалению, по вашему запросу ничего не найдено. Попробуйте изменить фильтры или уточнить запрос.",
                "metadata": {}
            }
            
        top_results = ranked[:3]
        response = "Вот что я подобрал для вас:\n"
        for t in top_results:
            score_pct = int(t.get('recommendation_score', 0) * 100)
            response += f"\n<TRACK_CARD id=\"{t['id']}\" score=\"{score_pct}\" />\n"
            response += f"{t['title']} — {t.get('specialization', '—')} ({t.get('region', '—')}, {t.get('format', '—')}).\n"
            if t.get("matched_skills"):
                response += f"Совпали навыки: {', '.join(t['matched_skills'][:5])}\n"
                
        response += "\nНапишите «ещё», чтобы увидеть другие варианты."
        
        return {
            "final_response": response,
            "metadata": {"results_count": len(ranked)}
        }
