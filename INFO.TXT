# Project Sandbox — Documento de Diseño Técnico v2.0

## 1. Visión General

Motor de simulación modular donde múltiples agentes (IAs o Humanos) interactúan en un entorno virtual persistente.

**Filosofía central:** "Código Tonto, Árbitro Inteligente". El código gestiona datos y estructura. La IA Árbitro gestiona lógica de consecuencias. Nunca al revés.

**Meta:** Un Core que hoy funcione en consola y mañana alimente una interfaz Web/Unity mediante WebSockets sin tocar la lógica interna.

---

## 2. Stack Tecnológico

| Componente | Tecnología | Motivo |
|---|---|---|
| Lenguaje | Python 3.11+ | asyncio mejorado, tipado moderno |
| API/Web | FastAPI | Asíncrono nativo, WebSockets integrados |
| Base de Datos | SQLite (modo WAL) | Portátil, sin servidor, suficiente para MVP |
| Validación | Pydantic + Instructor | Fuerza output JSON estructurado en la IA |
| Gestión de IAs | LiteLLM | Abstracción sobre OpenAI, Anthropic, Ollama, Azure |
| Formato de datos | JSON | Para configuración, estado del mundo y logs |

---

## 3. Arquitectura en Tres Capas

### A. Capa de Persistencia
Almacena la historia completa, no solo el estado final. Esto habilita el "Time Travel" (reproducir cualquier turno pasado) como consecuencia natural.

### B. El Núcleo (The Engine)
Bucle de eventos asíncrono. Nunca se bloquea.

Flujo por turno:
1. **Orquestador** — carga el estado del turno anterior desde BD
2. **Perception Filter** — genera una vista del mundo por agente (`get_visible_state`)
3. **Dispatcher** — envía el estado filtrado a todos los agentes en paralelo
4. **Collector** — espera los inputs con timeout por agente
5. **Arbitration** — envía conflictos al Árbitro IA
6. **Validator** — valida estructura *y* coherencia lógica del output
7. **Committer** — escribe el nuevo estado en BD y emite el evento de salida

### C. Capa de Adaptadores
El motor solo conoce la interfaz del Driver. No sabe si detrás hay GPT-4 o un humano en un móvil.

---

## 4. Estructura de Datos

### world_init.json
Toda la configuración del mundo vive aquí. Para crear un nuevo escenario, solo se crea un nuevo JSON. No se toca código.

```json
{
  "room_id": "habitacion_01",
  "turn_mode": "simultaneous",
  "agent_timeout_seconds": 60,
  "environment": {
    "temperature": 22,
    "light_level": 100,
    "description": "Una sala blanca acolchada sin ventanas."
  },
  "entities": [
    {
      "id": "item_bocadillo_99",
      "name": "Bocadillo de Jamón",
      "type": "item",
      "tags": ["comestible", "movible"],
      "attributes": { "nutricion": 50, "peso": 0.2 }
    },
    {
      "id": "agent_juan",
      "name": "Juan",
      "type": "agent",
      "driver": "openai_gpt4o",
      "attributes": { "hambre": 10, "salud": 100, "inventario": [] }
    }
  ]
}
```

**Campos clave:**
- `turn_mode`: `simultaneous` (todos actúan a la vez) o `sequential` (por orden). Afecta a todo el motor.
- `agent_timeout_seconds`: si un agente no responde, se registra acción nula y el turno continúa.

---

## 5. El Contrato del Driver

Todo driver, sea IA o humano, implementa obligatoriamente esta interfaz:

**`get_action(world_state, memory)`** — recibe el estado visible y el historial reciente. Devuelve una acción.

**`receive_feedback(turn_result)`** — recibe el resultado del turno una vez resuelto. Permite actualizar memoria interna y mostrar narrativa al jugador.

### Tipos de Driver disponibles

**Driver IA** — llama a una API LLM con el prompt construido por el sistema. Gestiona su propia ventana de memoria.

**Driver Humano (Consola)** — usa `asyncio.to_thread` para esperar input sin bloquear el loop.

**Driver Humano (Web)** — crea un `Future` al inicio del turno. El motor se pausa en ese agente. Cuando llega la acción por WebSocket, el endpoint inyecta el valor y desbloquea el motor.

**Driver Scripted** — ejecuta una lista de acciones predefinidas en orden. Uso exclusivo para testing y NPCs con comportamiento fijo. Permite desarrollar y depurar el Árbitro sin coste de API.

---

## 6. El Perception Filter

El núcleo nunca envía el `world_state` crudo a los agentes. Siempre pasa por `get_visible_state(agent_id, world_state)`.

Ejemplos de filtrado:
- Si `light_level` es 0, el agente no ve objetos, solo "oscuridad total".
- Un agente no recibe información de habitaciones donde no está.
- Atributos privados de otros agentes (ej: intenciones) no son visibles.

---

## 7. Memoria de los Agentes IA

El Driver IA construye el prompt en cada turno con esta estructura:

1. **System prompt** — personalidad y rol fijo del agente
2. **Contexto global filtrado** — solo lo relevante para su posición actual
3. **Ventana deslizante** — resumen de los últimos N turnos (configurable, recomendado: 10)
4. **Estado actual** — JSON de lo que percibe en este momento

No se envía el historial completo. Es caro, confunde al modelo y supera ventanas de contexto en simulaciones largas.

---

## 8. El Árbitro IA

### Flujo de resolución (two-pass)

**Paso 1 — Razonamiento libre:** el Árbitro recibe el estado del mundo y las intenciones de todos los agentes. Razona en texto plano sin restricciones de formato.

**Paso 2 — Extracción estructurada:** se usa `Instructor` + `Pydantic` para mapear ese razonamiento a un schema rígido. Si el output es inválido, la librería reenvía el error automáticamente para corrección.

### Schema del output del Árbitro

```
ResolucionArbitro:
  - razonamiento: texto libre explicando qué ocurre y por qué
  - narrativa: texto para mostrar al jugador
  - cambios: lista de CambioMundo
  - eventos: lista de etiquetas semánticas ["juan_obtiene_item", "conflicto_resuelto"]

CambioMundo:
  - accion: CREATE | UPDATE | DELETE
  - entity_id: identificador de la entidad afectada
  - atributo: campo que cambia
  - valor_anterior: para validar coherencia contra el estado actual
  - valor_nuevo: el valor resultante
```

### Validación lógica (The Validator)
Pydantic valida estructura. El Validator valida coherencia:
- ¿Existe la entidad que se quiere modificar?
- ¿Coincide `valor_anterior` con el estado actual en BD?
- ¿El cambio viola restricciones del mundo (ej: peso máximo de inventario)?

Si falla la validación lógica, se rechaza la resolución y se pide una nueva.

### Política de fallos del Árbitro
1. **Fallo de estructura** — Instructor reintenta automáticamente (hasta 3 veces)
2. **Fallo de coherencia** — el Validator rechaza y pide nueva resolución con contexto del error
3. **Fallo total** — el turno se marca como ERROR en BD, el mundo no cambia, el sistema continúa

---

## 9. Base de Datos

```sql
TABLE simulations
  id             TEXT PRIMARY KEY
  config_json    TEXT    -- world_init.json original completo
  created_at     TIMESTAMP
  status         TEXT    -- 'running' | 'paused' | 'finished'

TABLE turn_logs
  turn_id          INTEGER
  simulation_id    TEXT
  agents_inputs    TEXT        -- JSON: {agent_id: accion_raw}
  referee_decision TEXT        -- JSON: ResolucionArbitro validada
  world_state      TEXT        -- JSON: snapshot completo del mundo tras el turno
  status           TEXT        -- 'completed' | 'timeout' | 'error'
  created_at       TIMESTAMP
  PRIMARY KEY (turn_id, simulation_id)

TABLE events
  id             INTEGER PRIMARY KEY
  simulation_id  TEXT
  turn_id        INTEGER
  event_tag      TEXT    -- ej: 'juan_obtiene_item'
  entity_id      TEXT
```

La tabla `events` permite consultas semánticas sin parsear JSONs ("dame todos los turnos donde ocurrió un conflicto").

**Nota de diseño:** se guarda snapshot completo por turno. Es una decisión consciente para el MVP. El Time Travel es una consulta trivial. Si el tamaño del JSON crece a varios MB, migrar a checkpoints + deltas es el paso siguiente.

---

## 10. Roadmap

**Fase 1 — Core en Consola (MVP)**
Objetivo: validar que el Árbitro es coherente y divertido.
Entrega: script Python + SQLite. Un humano escribe, una IA responde.

**Fase 2 — API Headless**
Objetivo: desacoplar lógica de presentación.
Endpoints:
- `POST /simulation/create` — carga el world_init.json
- `POST /simulation/{id}/next_turn` — fuerza el siguiente turno
- `WS /simulation/{id}/stream` — canal de datos en tiempo real

**Fase 3 — Cliente Web**
Objetivo: visualización.
La web no tiene lógica de juego. Solo recibe JSON por WebSocket y pinta el estado. Tiene un slider de "línea de tiempo" que pide al backend el `world_state` del `turn_id` seleccionado.

---

## 11. Reglas para el Desarrollador

- **No uses Threads.** Usa `async/await` para toda I/O. El cuello de botella es esperar a GPT o al humano, no el CPU.
- **El Árbitro es Dios.** No programes reglas físicas en Python. `if fuego: quemar` no existe. Eso va en el prompt del Árbitro. En Python solo existe `apply_changes(json)`.
- **Separación estricta.** La clase `Agent` no importa `World`. Solo recibe datos.
- **Persistencia siempre.** No guardes estado en variables globales. Lee de BD, escribe en BD. Cada turno.
- **El Driver Scripted es tu mejor amigo.** Desarrolla y testea el Árbitro con él antes de gastar tokens.