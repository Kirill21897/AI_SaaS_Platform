from typing import Dict, List, Optional, Any
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    user_id: str
    profile: Dict[str, Any]
    filters: Dict[str, Any]

