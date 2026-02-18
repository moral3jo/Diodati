from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

# --- World Components ---

class Entity(BaseModel):
    id: str
    name: str
    type: Literal['agent', 'item', 'object']
    # Tags allow semantic querying (e.g. "edible", "movable")
    tags: List[str] = Field(default_factory=list)
    # Attributes are dynamic values (e.g. health, weight)
    attributes: Dict[str, Any] = Field(default_factory=dict)
    # Driver ID for agents (e.g. "openai_gpt4", "mock_ai")
    driver: Optional[str] = None

class Environment(BaseModel):
    temperature: float = 22.0
    light_level: float = 100.0
    description: str = ""

class WorldState(BaseModel):
    room_id: str
    turn_mode: Literal['sequential', 'simultaneous'] = 'sequential'
    agent_timeout_seconds: int = 60
    environment: Environment
    entities: List[Entity]

# --- Actions & Events ---

class AgentAction(BaseModel):
    agent_id: str
    action_type: str  # e.g., "MOVE", "TAKE", "TALK"
    target_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)  # Extra params

class WorldChange(BaseModel):
    action: Literal['CREATE', 'UPDATE', 'DELETE']
    entity_id: str
    attribute: Optional[str] = None
    value_previous: Any = None
    value_new: Any = None

class TurnResult(BaseModel):
    turn_id: int
    simulation_id: str
    # Logic resolution from the Arbitrator
    narrative: str
    changes: List[WorldChange]
    events: List[str] # Semantic tags for the turn, e.g. ["conflict_resolved"]
    # Snapshot after applying changes
    world_state: WorldState
