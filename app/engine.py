import asyncio
import json
import uuid
import logging
from typing import Dict, List
from .models import WorldState, AgentAction, TurnResult
from .db import DatabaseLog
from .db import DatabaseLog
from .drivers import BaseDriver, MockAIDriver, ScriptedDriver, APIDriver, HumanDriver, StaticFileDriver
from .drivers import BaseDriver, MockAIDriver, ScriptedDriver, APIDriver, HumanDriver, StaticFileDriver
from .arbitrator import MockArbitrator, LLMArbitrator

logger = logging.getLogger(__name__)

class SimulationEngine:
    def __init__(self, db_path: str = "simulation.db", arbitrator_type: str = "mock", ai_config: dict = None):
        self.db = DatabaseLog(db_path)
        self.ai_config = ai_config or {}
        
        if arbitrator_type == "llm" and ai_config:
            self.arbitrator = LLMArbitrator(
                reasoning_model=ai_config.get("arbitrator_reasoning"),
                formatting_model=ai_config.get("arbitrator_formatting")
            )
        else:
            self.arbitrator = MockArbitrator()
        self.drivers: Dict[str, BaseDriver] = {}
        self.simulation_id = None

    def initialize_simulation(self, config_path: str) -> str:
        """Loads the world_init.json and creates a new simulation."""
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Create unique ID
        sim_id = str(uuid.uuid4())
        self.simulation_id = sim_id
        
        # Save to DB
        self.db.create_simulation(sim_id, config_data)
        
        # Initialize initial state log (Turn 0)
        initial_state = WorldState(**config_data)
        
        # Hack: Guardar el turno 0 como completado para poder cargarlo después
        # En un sistema real, separaríamos "init" de "turns".
        self.db.save_turn(
            TurnResult(
                turn_id=0,
                simulation_id=sim_id,
                narrative="Inicio de la Simulación",
                changes=[],
                events=["init"],
                world_state=initial_state
            ),
            inputs={}
        )
        
        # Inicializar Drivers
        self._setup_drivers(initial_state)
        
        print(f"Simulación inicializada: {sim_id}")
        return sim_id

    def _setup_drivers(self, state: WorldState):
        for entity in state.entities:
            if entity.type == 'agent' and entity.driver:
                # Factory pattern for drivers
                if entity.driver == 'mock_ai':
                    self.drivers[entity.id] = MockAIDriver(entity.id)
                elif entity.driver == 'scripted':
                    # Placeholder for scripted
                    self.drivers[entity.id] = ScriptedDriver(entity.id, [])
                elif entity.driver == 'api':
                    # Configuración dinámica por agente
                    model = self.ai_config.get(f"agent_{entity.id}", self.ai_config.get("agent_default"))
                    self.drivers[entity.id] = APIDriver(entity.id, model_name=model)
                elif entity.driver == 'human':
                    self.drivers[entity.id] = HumanDriver(entity.id)
                elif entity.driver == 'static':
                    self.drivers[entity.id] = StaticFileDriver(entity.id)
                else:
                    logger.warning(f"Unknown driver type {entity.driver} for {entity.id}")

    async def run_turn(self) -> TurnResult:
        if not self.simulation_id:
            raise ValueError("Simulation not initialized")

        # 1. Load generic state (last turn)
        last_state_dict = self.db.load_last_state(self.simulation_id)
        current_state = WorldState(**last_state_dict)
        current_turn_id = self._get_next_turn_id()

        print(f"\n--- Procesando Turno {current_turn_id} ---")

        # 2. Collect actions (Parallel)
        agent_actions: List[AgentAction] = []
        action_coros = []
        
        for agent_id, driver in self.drivers.items():
            # Filter state (Perception Filter - simplified: send all)
            visible_state = current_state 
            action_coros.append(driver.get_action(visible_state))

        results = await asyncio.gather(*action_coros, return_exceptions=True)
        
        inputs_for_log = {}
        for res in results:
            if isinstance(res, AgentAction):
                agent_actions.append(res)
                inputs_for_log[res.agent_id] = res.model_dump()
            else:
                logger.error(f"Error getting action: {res}")

        # 3. Arbitrate
        turn_result = self.arbitrator.resolve_turn(
            current_state, agent_actions, current_turn_id, self.simulation_id
        )

        # 4. Save to DB
        self.db.save_turn(turn_result, inputs_for_log)

        # 5. Feedback to drivers
        feedback_coros = [d.receive_feedback(turn_result) for d in self.drivers.values()]
        await asyncio.gather(*feedback_coros)
        
        print(f"Turno {current_turn_id} completado. Narrativa: {turn_result.narrative}")
        return turn_result

    async def run_steps(self, steps: int):
        for _ in range(steps):
            await self.run_turn()

    def _get_next_turn_id(self) -> int:
        import sqlite3
        with sqlite3.connect(self.db.db_path) as conn:
            cursor = conn.execute("SELECT MAX(turn_id) FROM turn_logs WHERE simulation_id = ?", (self.simulation_id,))
            row = cursor.fetchone()
            # If no turns yet (only init id 0), next is 1. If init is 0, max is 0, so 0+1=1.
            return (row[0] if row[0] is not None else -1) + 1

