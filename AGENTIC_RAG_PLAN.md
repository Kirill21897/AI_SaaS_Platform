# 🚀 Agentic RAG Implementation Plan - LangGraph Architecture

## 📋 Executive Summary

Переход с текущей **статичной RAG системы** на **динамичный agentic RAG** с LangGraph, позволяющий:
- ✅ Multi-step reasoning и reflection
- ✅ Адаптивный tool selection
- ✅ Улучшенное переранжирование результатов
- ✅ Контекстная память разговора
- ✅ Обработка сложных многошаговых запросов

---

## 🎯 Architecture Overview

### Current Pain Points ❌
1. **Static 40/60 weighting** - не адаптируется к контексту
2. **Limited reasoning** - только 1 проход поиска
3. **No reflection** - нет проверки результатов
4. **Brittle routing** - жесткие детерминистические правила
5. **No clarification loop** - нет переговорки для уточнения

### New Architecture ✅
```
User Message
    ↓
[ReasoningAgent] ← LangGraph node
  ├─ Understand intent/context
  ├─ Decide strategy (depth vs breadth)
  └─ Route to best tools
    ↓
[ToolExecutor] ← Parallel tool calls
  ├─ search_tracks(semantic)
  ├─ filter_tracks(hard filters)
  ├─ analyze_skills(matching)
  └─ fetch_related_content(enrichment)
    ↓
[EvaluatorAgent]
  ├─ Score results (dynamic weights)
  ├─ Detect gaps in results
  ├─ Decide if need more context
    ↓
[ReflectionAgent] (optional)
  ├─ Compare to user intent
  ├─ Generate clarifying question
  ├─ Suggest alternative searches
    ↓
[ResponseBuilder]
  ├─ Format results with explanations
  ├─ Add metadata/confidence scores
  └─ Return to user
```

---

## 📦 New Dependencies

```python
# requirements-agentic-rag.txt
langchain>=0.1.0
langgraph>=0.0.1
langchain-community>=0.0.1
langchain-openai>=0.0.1          # or langchain-ollama
langsmith>=0.0.1                  # debugging & monitoring
pydantic-ai>=0.1.0               # structured output validation

# Keep existing
langchain-qdrant>=0.1.0          # LangChain Qdrant integration
```

---

## 🏗️ Implementation Plan

### Phase 1: Foundation Setup (Days 1-2)
- [ ] Install LangGraph + dependencies
- [ ] Create `AIGraphBuilder` class for graph construction
- [ ] Implement state schema with `TypedDict`
- [ ] Setup `rag_tools.py` with core tools

### Phase 2: Tool Layer (Days 2-3)
- [ ] **search_tracks_tool**: semantic + keyword hybrid search
- [ ] **filter_tracks_tool**: advanced SQL filtering
- [ ] **analyze_skill_match_tool**: detailed skill comparison
- [ ] **fetch_track_details_tool**: enrichment with related content
- [ ] **list_filters_tool**: get available filter options
- [ ] **clarify_intent_tool**: ask clarifying questions

### Phase 3: Agent Nodes (Days 3-5)
- [ ] **reasoning_node**: intent analysis + strategy selection
- [ ] **tool_executor_node**: orchestrate tool calls
- [ ] **evaluator_node**: score & rank results
- [ ] **reflection_node**: check quality & suggest improvements
- [ ] **response_builder_node**: format final response

### Phase 4: Graph & Flow (Days 5-6)
- [ ] Define state graph with conditional edges
- [ ] Implement loop-back logic for iterative refinement
- [ ] Add memory management (Redis session state)
- [ ] Implement streaming output
- [ ] Add error handling & fallbacks

### Phase 5: Integration & Testing (Days 6-7)
- [ ] Replace old `orchestrator.py` with new graph
- [ ] Update FastAPI endpoints to use LangGraph
- [ ] Test with various query types
- [ ] Performance & latency benchmarking
- [ ] Add LangSmith tracing

---

## 🛠️ Key Components Design

### 1. State Schema (TypedDict)

```python
# backend/ai_engine/agentic_rag/state.py
class RAGState(TypedDict):
    # Input
    user_message: str
    user_id: str
    profile: Dict  # cached user profile
    filters: Dict  # {specialization, format, region}
    
    # Reasoning phase
    intent: str  # "recommend", "search", "filter", "clarify"
    strategy: str  # "narrow", "broad", "exploratory"
    reasoning: str  # LLM's reasoning
    
    # Execution phase
    search_results: List[Dict]  # raw search results
    filtered_results: List[Dict]  # after hard filters
    skill_scores: Dict  # {track_id: score}
    
    # Evaluation phase
    ranked_results: List[Dict]  # final ranked with confidence
    quality_score: float  # 0-1 how good are results
    needs_refinement: bool
    clarifying_question: Optional[str]
    
    # Response phase
    final_response: str
    metadata: Dict  # confidence, sources, etc
    
    # Context/Memory
    conversation_history: List[Dict]
    previous_searches: List[Dict]
    iteration_count: int
```

### 2. Tool Definitions

```python
# backend/ai_engine/agentic_rag/tools.py

@tool
def search_tracks(
    query: str,
    limit: int = 15,
    with_embeddings: bool = False
) -> List[Dict]:
    """Semantic search in Qdrant + keyword fallback"""

@tool
def filter_tracks(
    tracks: List[Dict],
    specialization: Optional[str] = None,
    format: Optional[str] = None,
    region: Optional[str] = None,
    min_skill_match: float = 0.3
) -> List[Dict]:
    """Advanced SQL filtering with optional skill matching"""

@tool
def analyze_skill_match(
    user_skills: List[str],
    track_required_skills: Dict[str, float]
) -> Dict:
    """
    Detailed skill analysis
    Returns: {
        matched_skills: [],
        missing_skills: [],
        match_score: float,
        explanation: str
    }
    """

@tool
def fetch_track_details(
    track_id: int
) -> Dict:
    """Fetch full track info + related content"""

@tool
def clarify_intent(
    user_message: str,
    context: str
) -> str:
    """Ask LLM for clarifying question"""
```

### 3. Agent Nodes

```python
# backend/ai_engine/agentic_rag/nodes.py

def reasoning_node(state: RAGState) -> RAGState:
    """
    Analyze user intent using LLM
    - Determine if searching, filtering, or clarifying
    - Decide breadth (many results) vs depth (detailed analysis)
    - Route to appropriate tools
    """

def tool_executor_node(state: RAGState) -> RAGState:
    """
    Execute selected tools in parallel
    - Gather search_results, filters, skill scores
    - Handle tool errors gracefully
    """

def evaluator_node(state: RAGState) -> RAGState:
    """
    Score and rank results
    - Dynamic weighting based on intent
    - Filter low-confidence results
    - Detect if need more context
    """

def reflection_node(state: RAGState) -> RAGState:
    """
    Optional reflective step
    - Compare results to original intent
    - Suggest alternative searches
    - Ask clarifying questions if needed
    """

def response_builder_node(state: RAGState) -> RAGState:
    """
    Format final response for user
    - Add explanations for each result
    - Include confidence scores
    - Suggest next actions
    """
```

### 4. Graph Definition

```python
# backend/ai_engine/agentic_rag/graph.py

def build_rag_graph() -> StateGraph:
    graph = StateGraph(RAGState)
    
    # Add nodes
    graph.add_node("reasoning", reasoning_node)
    graph.add_node("tool_executor", tool_executor_node)
    graph.add_node("evaluator", evaluator_node)
    graph.add_node("reflection", reflection_node)
    graph.add_node("response_builder", response_builder_node)
    
    # Add edges
    graph.add_edge("START", "reasoning")
    
    # Conditional edge: need clarification?
    graph.add_conditional_edges(
        "reasoning",
        needs_clarification_check,
        {
            True: "reflection",
            False: "tool_executor"
        }
    )
    
    # Tool executor → Evaluator
    graph.add_edge("tool_executor", "evaluator")
    
    # Evaluator → Reflection or Response
    graph.add_conditional_edges(
        "evaluator",
        quality_check,
        {
            "needs_refinement": "reflection",
            "good_quality": "response_builder",
            "poor_quality": "reasoning"  # loop back
        }
    )
    
    graph.add_edge("reflection", "response_builder")
    graph.add_edge("response_builder", "END")
    
    return graph.compile()
```

---

## 🎯 Dynamic Weighting Strategy

Instead of static 40/60, use context-aware weights:

```python
def calculate_dynamic_weights(state: RAGState) -> Dict[str, float]:
    """
    Adjust weights based on intent and strategy
    """
    base_weights = {
        "semantic_relevance": 0.4,
        "skill_match": 0.6
    }
    
    # Strategy adjustments
    if state.strategy == "narrow":
        base_weights["skill_match"] = 0.7  # stricter matching
    elif state.strategy == "broad":
        base_weights["semantic_relevance"] = 0.6  # more exploration
    
    # Intent adjustments
    if state.intent == "clarify":
        base_weights["semantic_relevance"] = 0.8  # explore broadly
    
    return base_weights
```

---

## 📊 Example: Complex Query Flow

### Query: "Покажи мне backend треки для junior с remote форматом в Москве"

```
1. REASONING NODE
   intent: "recommend"
   strategy: "narrow"
   reasoning: "User wants filtered recommendations with multiple constraints"
   
2. TOOL EXECUTOR
   → search_tracks("backend junior remote Москва") → [T1, T2, ..., T15]
   → filter_tracks(..., specialization="backend", format="remote", region="Москва")
      → [T1, T5, T8] (only 3 passed)
   → analyze_skill_match(user_skills, each_track.required_skills)
      → skill_scores = {T1: 0.85, T5: 0.72, T8: 0.68}
   
3. EVALUATOR NODE
   Quality assessment:
   - semantic_scores from Qdrant: [0.92, 0.78, 0.65]
   - skill_scores: [0.85, 0.72, 0.68]
   - Final: [(T1: 0.88), (T5: 0.75), (T8: 0.67)]
   
   quality_score = 0.88 (HIGH) → good_quality
   
4. RESPONSE BUILDER
   Output:
   {
     "results": [
       {
         "id": 1,
         "title": "...",
         "explanation": "Отличное совпадение (88% уверенность). Все ваши навыки релевантны.",
         "matched_skills": ["python", "fastapi", "docker"],
         "missing_skills": ["kubernetes"],
         "recommendation_score": 0.88
       },
       ...
     ],
     "summary": "Found 3 perfect matches for your profile",
     "next_suggestions": [...]
   }
```

---

## 🔄 Multi-Turn Conversation

Использовать LangGraph для сохранения состояния между сообщениями:

```python
# Persistent state in Redis
session_state = {
    "user_id": "user_123",
    "conversation_history": [
        {"role": "user", "content": "backend tracks"},
        {"role": "assistant", "content": "Found 5 tracks..."},
        {"role": "user", "content": "только remote"}  # follow-up
    ],
    "graph_state": RAGState(...)  # full state
}
```

---

## 🚀 Migration Path

### Week 1: Foundation
```
old_orchestrator.py → keep as backup
new_agentic_rag/ → build in parallel
```

### Week 2: Switch
```
/api/v1/chat/stream → switch to LangGraph
Run A/B tests if needed
```

### Week 3: Optimize
```
Tune weights
Add LangSmith tracing
Performance optimization
```

---

## 📈 Success Metrics

- [ ] **Accuracy**: % of results matching user intent (target: 95%+)
- [ ] **Latency**: <2s for typical query (target)
- [ ] **Disambiguation**: Users need clarification <5% of time
- [ ] **User Satisfaction**: Positive feedback on recommendations
- [ ] **Tool Utilization**: Agents using all tools appropriately

---

## 📚 References

- LangGraph Docs: https://langchain-ai.github.io/langgraph/
- LangChain Tools: https://python.langchain.com/docs/modules/tools/
- Qdrant Integration: https://python.langchain.com/docs/integrations/vectorstores/qdrant
- State Machines: https://langchain-ai.github.io/langgraph/concepts/agentic_patterns/

---

## 🎬 Next Steps

1. ✅ Understand current architecture (DONE)
2. ⏳ Review this plan & decide modifications
3. ⏳ Install dependencies
4. ⏳ Create state schema
5. ⏳ Implement tools
6. ⏳ Build graph nodes
7. ⏳ Integrate with FastAPI
8. ⏳ Test & optimize

**Ready to start Phase 1? Let me know!**
