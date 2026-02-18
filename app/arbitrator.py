from typing import List, Dict, Any
import random
import json
import os
from abc import ABC, abstractmethod
from .models import WorldState, AgentAction, TurnResult, WorldChange, Entity
from litellm import completion

class Arbitrator(ABC):
    @abstractmethod
    def resolve_turn(self, state: WorldState, actions: List[AgentAction], turn_id: int, simulation_id: str) -> TurnResult:
        pass

class LLMArbitrator(Arbitrator):
    def __init__(self, reasoning_model: str, formatting_model: str):
        self.reasoning_model = reasoning_model
        self.formatting_model = formatting_model

    def resolve_turn(self, state: WorldState, actions: List[AgentAction], turn_id: int, simulation_id: str) -> TurnResult:
        # 1. Preparar Contexto
        context_str = self._build_context(state, actions)
        
        # 2. Llamada 1: Razonamiento (Thinking)
        print(f"   [LLM] Razonando turno {turn_id}...")
        reasoning_response = completion(
            model=self.reasoning_model,
            messages=[
                {"role": "system", "content": self._get_system_prompt_reasoning()},
                {"role": "user", "content": context_str}
            ]
        )
        reasoning_content = reasoning_response.choices[0].message.content
        # print(f"   [DEBUG-LLM] Reasoning: {reasoning_content[:100]}...")

        # 3. Llamada 2: Formateo (Formatting)
        print(f"   [LLM] Formateando resultado...")
        formatting_response = completion(
            model=self.formatting_model, 
            messages=[
                {"role": "system", "content": self._get_system_prompt_formatting()},
                {"role": "user", "content": f"CONTEXTO ORIGINAL:\n{context_str}\n\nTU RAZONAMIENTO:\n{reasoning_content}\n\nGenera AHORA el JSON válido."}
            ],
            response_format={ "type": "json_object" }
        )
        formatted_content = formatting_response.choices[0].message.content
        
        try:
            # Limpiar posible markdown ```json ... ```
            clean_json = formatted_content.replace("```json", "").replace("```", "").strip()
            result_dict = json.loads(clean_json)
            
            # Asegurar campos mínimos
            result_dict["turn_id"] = turn_id
            result_dict["simulation_id"] = simulation_id
            if "world_state" not in result_dict:
                # Fallback horrible si la IA falla catastróficamente
                result_dict["world_state"] = state.model_dump()
            
            return TurnResult(**result_dict)
            
        except json.JSONDecodeError as e:
            print(f"ERROR JSON LLM: {e}")
            print(formatted_content)
            # Fallback de emergencia
            return TurnResult(
                turn_id=turn_id,
                simulation_id=simulation_id,
                narrative="La realidad se quebró (Error de la IA).",
                changes=[],
                events=["error_ai"],
                world_state=state
            )

    def _build_context(self, state: WorldState, actions: List[AgentAction]) -> str:
        actions_desc = []
        for a in actions:
            target_str = f" sobre {a.target_id}" if a.target_id else ""
            payload_str = f" ({a.payload})" if a.payload else ""
            actions_desc.append(f"- Agente {a.agent_id} intenta {a.action_type}{target_str}{payload_str}")
        
        return f"""
ESTADO ACTUAL DEL MUNDO:
{state.model_dump_json(indent=2)}

ACCIONES PROPUESTAS POR LOS AGENTES:
{chr(10).join(actions_desc)}
"""

    def _get_system_prompt_reasoning(self) -> str:
        return """
Eres el Árbitro (Motor Físico) de la simulación Project Sandbox.
Tu trabajo es decidir fríamente qué sucede basándote en la lógica y los atributos.

REGLAS DE RESOLUCIÓN:
1. "TALK": Decide si el mensaje cambia el estado mental del receptor.
2. "TAKE": Si hay conflicto, gana quien tenga mayor atributo relevante (fuerza, velocidad, hambre) o azar.
3. CONSECUENCIAS: Sé estricto. Si no tienen el objeto, no pueden usarlo.

REGLAS DE NARRATIVA (IMPORTANTE):
- Sé CONCISO y OBJETIVO. Estilo "Informe Policial" o "Log de Videojuego".
- Máximo 2-3 frases.
- Describe la ACCIÓN física y el RESULTADO.
- Evita metáforas, drama innecesario o leer la mente de los personajes ("sintió resignación").
- Céntrate en lo que se ve desde fuera.

Tu salida debe ser un análisis paso a paso de lo que ocurre.
"""

    def _get_system_prompt_formatting(self) -> str:
        return """
Eres un formateador de datos JSON.
Tu tarea:
1. Extrae los CAMBIOS exactos (CREATE/UPDATE/DELETE) del razonamiento.
2. Genera un resumen narrativo de UNA sola frase para el campo "narrative".
3. Devuelve el JSON válido que cumpla con el esquema `TurnResult`.

El esquema es:
{
  "narrative": "Resumen de UNA sola frase.",
  "changes": [
    {
       "action": "UPDATE" | "CREATE" | "DELETE",
       "entity_id": "string",
       "attribute": "string (opcional)",
       "value_previous": "any (opcional)",
       "value_new": "any (opcional)"
    }
  ],
  "events": ["string (etiquetas, ej: 'conflict_resolved')"],
  "world_state": { ... objeto WorldState completo actualizado ... }
}

IMPORTANTE: 
- `changes` debe ser una LISTA DE OBJETOS, NO strings. Si no hay cambios de datos, pon [].
- Debes devolver el `world_state` COMPLETO.
- Responde SOLO con el JSON.
"""

class MockArbitrator(Arbitrator):
    """
    Reemplaza al Árbitro LLM para el MVP.
    Implementa lógica hardcodeada para acciones básicas como TAKE, DROP, WAIT.
    Ahora soporta RESOLUCIÓN DE CONFLICTOS.
    """
    
    def resolve_turn(self, state: WorldState, actions: List[AgentAction], turn_id: int, sim_id: str) -> TurnResult:
        changes: List[WorldChange] = []
        events: List[str] = []
        narrative_lines: List[str] = []
        
        current_entities = {e.id: e for e in state.entities}
        
        # 1. Agrupar acciones por tipo/objetivo para detectar conflictos
        take_requests: Dict[str, List[str]] = {} # item_id -> [agent_id, ...]
        
        for action in actions:
            agent_name = next((e.name for e in state.entities if e.id == action.agent_id), action.agent_id)
            
            if action.action_type == "TALK":
                 msg = action.payload.get("message", "...")
                 narrative_lines.append(f'{agent_name} grita: "{msg}"')
            
            elif action.action_type == "TAKE":
                target_id = action.target_id
                if target_id not in take_requests:
                    take_requests[target_id] = []
                take_requests[target_id].append(action.agent_id)
            
            elif action.action_type == "WAIT":
                narrative_lines.append(f"{agent_name} mira a su alrededor nerviosamente.")

        # 2. Resolver conflictos de TAKE
        for item_id, agents in take_requests.items():
            item = current_entities.get(item_id)
            if not item:
                continue

            if len(agents) == 1:
                # Éxito
                winner_id = agents[0]
                winner_name = next((e.name for e in state.entities if e.id == winner_id), winner_id)
                self._apply_take_success(winner_id, winner_name, item, changes, narrative_lines, events, state)
            else:
                # ¡Conflicto!
                winner_id = random.choice(agents)
                winner_name = next((e.name for e in state.entities if e.id == winner_id), winner_id)
                losers = [a for a in agents if a != winner_id]
                losers_names = [next((e.name for e in state.entities if e.id == a), a) for a in losers]
                
                narrative_lines.append(f"¡CONFLICTO! {', '.join(losers_names)} y {winner_name} pelean por el objeto {item.name}.")
                narrative_lines.append(f"¡{winner_name} empuja a los demás y lo agarra!")
                
                self._apply_take_success(winner_id, winner_name, item, changes, narrative_lines, events, state)
                events.append("conflict_occurred")

        # Apply changes to generate the new state snapshot
        new_state = self._apply_changes(state, changes)
        
        return TurnResult(
            turn_id=turn_id,
            simulation_id=sim_id,
            narrative=" ".join(narrative_lines),
            changes=changes,
            events=events,
            world_state=new_state
        )

    def _apply_take_success(self, agent_id: str, agent_name: str, item: Entity, changes: List[WorldChange], narrative: List[str], events: List[str], state: WorldState):
        # 1. Remove item from world entities
        changes.append(WorldChange(
            action='DELETE',
            entity_id=item.id
        ))
        
        # 2. Update agent inventory
        # Find agent current attributes to modify
        agent = next((e for e in state.entities if e.id == agent_id), None)
        if agent:
            new_attrs = agent.attributes.copy()
            inventory = new_attrs.get("inventario", [])
            inventory.append(item.id)
            new_attrs["inventario"] = inventory
            
            changes.append(WorldChange(
                action='UPDATE',
                entity_id=agent_id,
                attribute='attributes',
                value_previous=agent.attributes,
                value_new=new_attrs
            ))
        
        narrative.append(f"{agent_name} toma exitosamente el objeto {item.name}.")
        events.append(f"{agent_id}_took_{item.id}")

    def _apply_changes(self, state: WorldState, changes: List[WorldChange]) -> WorldState:
        # Deep copy
        new_entities = [e.model_copy() for e in state.entities]
        
        for change in changes:
            if change.action == 'DELETE':
                new_entities = [e for e in new_entities if e.id != change.entity_id]
            elif change.action == 'UPDATE':
                for e in new_entities:
                    if e.id == change.entity_id:
                        if change.attribute == 'attributes':
                            e.attributes = change.value_new
                        
        return WorldState(
            room_id=state.room_id,
            turn_mode=state.turn_mode,
            agent_timeout_seconds=state.agent_timeout_seconds,
            environment=state.environment,
            entities=new_entities
        )
