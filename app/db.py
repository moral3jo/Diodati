import sqlite3
import json
import logging
from typing import Optional, Dict, Any
from .models import WorldState, TurnResult

logger = logging.getLogger(__name__)

class DatabaseLog:
    def __init__(self, db_path: str = "simulation.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            # Simulation config table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS simulations (
                    id TEXT PRIMARY KEY,
                    config_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT
                )
            """)
            # Turn logs table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS turn_logs (
                    turn_id INTEGER,
                    simulation_id TEXT,
                    agents_inputs TEXT,
                    referee_decision TEXT, 
                    world_state TEXT,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (turn_id, simulation_id)
                )
            """)
            # Events table (for semantic search)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    simulation_id TEXT,
                    turn_id INTEGER,
                    event_tag TEXT,
                    entity_id TEXT
                )
            """)

    def create_simulation(self, sim_id: str, config: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO simulations (id, config_json, status) VALUES (?, ?, ?)",
                (sim_id, json.dumps(config), "running")
            )

    def load_last_state(self, sim_id: str) -> Optional[Dict[str, Any]]:
        """Returns the world state from the last completed turn, or None if new."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT world_state FROM turn_logs WHERE simulation_id = ? ORDER BY turn_id DESC LIMIT 1",
                (sim_id,)
            )
            row = cursor.fetchone()
            if row:
                return json.loads(row[0])
            return None

    def save_turn(self, turn_result: TurnResult, inputs: Dict[str, Any]):
        with sqlite3.connect(self.db_path) as conn:
            # Save main log
            conn.execute(
                """
                INSERT INTO turn_logs 
                (turn_id, simulation_id, agents_inputs, referee_decision, world_state, status)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    turn_result.turn_id,
                    turn_result.simulation_id,
                    json.dumps(inputs),
                    json.dumps({
                        "narrative": turn_result.narrative,
                        "changes": [c.model_dump() for c in turn_result.changes]
                    }),
                    turn_result.world_state.model_dump_json(),
                    "completed"
                )
            )
            
            # Index events
            for event in turn_result.events:
                conn.execute(
                    "INSERT INTO events (simulation_id, turn_id, event_tag) VALUES (?, ?, ?)",
                    (turn_result.simulation_id, turn_result.turn_id, event)
                )
