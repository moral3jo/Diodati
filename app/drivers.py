from abc import ABC, abstractmethod
from typing import List, Dict, Any
from .models import WorldState, TurnResult, AgentAction
import random
import asyncio
import json
import os

class BaseDriver(ABC):
    def __init__(self, agent_id: str):
        self.agent_id = agent_id

    @abstractmethod
    async def get_action(self, visible_state: WorldState) -> AgentAction:
        """Decide an action based on the visible state."""
        pass

    @abstractmethod
    async def receive_feedback(self, turn_result: TurnResult):
        """Receive the result of the turn to update internal memory."""
        pass

class MockAIDriver(BaseDriver):
    """
    A dumb AI that picks random available actions to simulate behavior.
    """
    async def get_action(self, visible_state: WorldState) -> AgentAction:
        # Heurística simple: si hay un objeto, 50% de probabilidad de TOMAR, 50% de HABLAR (discutir).
        # De lo contrario, esperar.
        
        items = [e for e in visible_state.entities if e.type == 'item']
        
        if items:
            target = random.choice(items)
            # Aleatorizar comportamiento
            if random.random() < 0.5:
                return AgentAction(
                    agent_id=self.agent_id,
                    action_type="TAKE",
                    target_id=target.id,
                    payload={"reason": "Es mio!"}
                )
            else:
                return AgentAction(
                    agent_id=self.agent_id,
                    action_type="TALK",
                    target_id=target.id,
                    payload={"message": f"¡Oye! ¡Ese {target.name} es mío!"}
                )
        
        return AgentAction(
            agent_id=self.agent_id,
            action_type="WAIT",
            payload={"reason": "Aburrido..."}
        )

    async def receive_feedback(self, turn_result: TurnResult):
        pass

class APIDriver(BaseDriver):
    """
    Esqueleto para futura integración con LLMs reales (Fase 1/2).
    """
    def __init__(self, agent_id: str, model_name: str = "groq/llama-3.1-8b-instant"):
        super().__init__(agent_id)
        self.model_name = model_name
    
    async def get_action(self, visible_state: WorldState) -> AgentAction:
        # TODO: Implementar llamada a API real
        # Por ahora devuelve WAIT
        return AgentAction(
            agent_id=self.agent_id,
            action_type="WAIT",
            payload={"reason": "Esperando implementación de API..."}
        )

    async def receive_feedback(self, turn_result: TurnResult):
        pass

class HumanDriver(BaseDriver):
    """
    Permite interacción por consola. Usa asyncio.to_thread para no bloquear.
    """
    async def get_action(self, visible_state: WorldState) -> AgentAction:
        print(f"\n[HUMANO] Turno de {self.agent_id}. Estado visible:")
        print(f"  Ubicación: {visible_state.room_id}")
        print(f"  Entidades: {[e.name for e in visible_state.entities]}")
        
        # Ejecutar input() en un thread separado para no bloquear el event loop
        action_str = await asyncio.to_thread(input, f"  Acción para {self.agent_id} (TAKE <id> | TALK <msg> | WAIT): ")
        
        parts = action_str.strip().split(" ", 1)
        action_type = parts[0].upper()
        
        if action_type == "TAKE":
            target_id = parts[1] if len(parts) > 1 else ""
            return AgentAction(agent_id=self.agent_id, action_type="TAKE", target_id=target_id)
        elif action_type == "TALK":
            msg = parts[1] if len(parts) > 1 else "..."
            return AgentAction(agent_id=self.agent_id, action_type="TALK", payload={"message": msg})
        else:
            return AgentAction(agent_id=self.agent_id, action_type="WAIT")

    async def receive_feedback(self, turn_result: TurnResult):
        print(f"\n[HUMANO] Feedback para {self.agent_id}:")
        print(f"  Narrativa: {turn_result.narrative}")

class StaticFileDriver(BaseDriver):
    """
    Lee respuestas de archivos JSON locales.
    Ruta: c:/PROYECTOS/IAS/responses/{agent_id}.json
    """
    def __init__(self, agent_id: str):
        super().__init__(agent_id)
        self.responses_path = f"responses/{agent_id}.json"
        self.current_turn = 0
        self._load_responses()

    def _load_responses(self):
        self.responses = {}
        if os.path.exists(self.responses_path):
            with open(self.responses_path, 'r', encoding='utf-8') as f:
                self.responses = json.load(f)

    async def get_action(self, visible_state: WorldState) -> AgentAction:
        # Intentar obtener respuesta para el turno actual (o "default")
        # Asumimos que el engine incrementa el turno, pero aquí llevamos un contador simple
        # O idealmente recibimos el turn_id en el estado, pero WorldState no lo tiene (fallo de diseño MVP)
        # Usaremos un contador interno por ahora.
        self.current_turn += 1
        
        turn_key = str(self.current_turn)
        action_data = self.responses.get(turn_key) or self.responses.get("default")
        
        if action_data:
            return AgentAction(
                agent_id=self.agent_id,
                action_type=action_data.get("action_type", "WAIT"),
                target_id=action_data.get("target_id"),
                payload=action_data.get("payload", {})
            )
        
        return AgentAction(agent_id=self.agent_id, action_type="WAIT", payload={"reason": "No script logic"})

    async def receive_feedback(self, turn_result: TurnResult):
        pass
class ScriptedDriver(BaseDriver):
    """
    Ejecuta una secuencia estricta de acciones. Bueno para pruebas.
    """
    def __init__(self, agent_id: str, script: List[AgentAction]):
        super().__init__(agent_id)
        self.script = script
        self.step = 0

    async def get_action(self, visible_state: WorldState) -> AgentAction:
        if self.step < len(self.script):
            action = self.script[self.step]
            self.step += 1
            return action
        return AgentAction(agent_id=self.agent_id, action_type="WAIT")

    async def receive_feedback(self, turn_result: TurnResult):
        pass
