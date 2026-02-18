# Project Sandbox MVP

**Motor de simulación emergente impulsado por IAs.**

Project Sandbox es un **motor de simulación agnóstico** donde agentes (IAs o Humanos) interactúan en un entorno virtual persistente.
La filosofía central es **"Código Tonto, Árbitro Inteligente"**: el código solo gestiona el movimiento de datos, mientras que un Gran Modelo de Lenguaje (LLM) actúa como "Motor Físico" y Juez, decidiendo las consecuencias de cada acción.

---

## 🚀 Cómo Empezar

### Requisitos
- Python 3.11+
- Una API Key de **Groq** (para Llama 3) o **Google Gemini**.

### Instalación

1.  **Clonar y preparar entorno:**
    ```bash
    git clone https://github.com/TU_USUARIO/TU_REPO.git
    cd IAS
    python -m venv venv
    .\venv\Scripts\activate  # Windows
    # source venv/bin/activate # Linux/Mac
    pip install -r requirements.txt
    ```

2.  **Configurar Variables:**
    Copia el ejemplo y edítalo con tus claves:
    ```bash
    cp .env.example .env
    ```
    Edita `.env` y añade tu `GROQ_API_KEY`.

3.  **Ejecutar Simulación:**
    ```bash
    python main.py
    ```

---

## 🧠 Arquitectura Multi-Modelo

Este proyecto no usa una sola IA. Usa un **enjambre de modelos especializados** para optimizar costes y latencia (ver `app/ai_config.py`).

| Rol | Función | Modelo Recomendado (Tier 1) | Motivo |
|---|---|---|---|
| **Cerebro (Reasoning)** | Árbitro. Decide qué pasa y resuelve conflictos. | `groq/llama-3.3-70b-versatile` | Necesita máxima lógica e inteligencia. 1k req/día. |
| **Secretario (Formatting)** | Traduce la narrativa a JSON estricto. | `groq/llama-3.1-8b-instant` | Necesita obediencia ciega a esquemas. 14k req/día. |
| **Actores (NPCs)** | Roleplay de los personajes (Juan, Pedro). | `groq/llama-3.1-8b-instant` | Velocidad y creatividad. |

> **Nota:** El sistema soporta fallback y cambio "en caliente" editando `app/ai_config.py`.

---

## ⚙️ Estructura del Proyecto

- **`main.py`**: Punto de entrada. Carga configuración e inicia el bucle.
- **`app/engine.py`**: El corazón. Gestiona el bucle de eventos (Percibir -> Actuar -> Arbitrar -> Guardar).
- **`app/arbitrator.py`**: La lógica del Árbitro. Contiene los Prompts del Sistema y el flujo de 2 pasos (Think -> Format).
- **`app/ai_config.py`**: Matriz de asignación de modelos por rol.
- **`app/drivers.py`**: Adaptadores para los agentes (Mock, Scripted, API, Humano).
- **`world_init.json`**: Configuración inicial del mundo (habitaciones, items, agentes).

---

## 🛠️ Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Lenguaje | **Python 3.14** (Asyncio Nativo) |
| Gestión IAs | **LiteLLM** (Abstracción universal de APIs) |
| IA Principal | **Groq LPU** (Inferencia ultra-rápida) |
| Base de Datos | **SQLite** + JSON Logs (Persistencia total) |
| Configuración | **Dotenv** + JSON |

---

## 🔮 Roadmap & TODOs

### Próximos Pasos (Core Engine)
- [ ] **Sistema de Iniciativa:** Turnos basados en velocidad, no round-robin fijo.
- [ ] **Propagación del Sonido:** Que "gritar" en una sala alerte a las adyacentes.
- [ ] **Tier List Automática:** Sistema de fallback. Si Llama-70b falla, saltar a Qwen-32b automáticamente.

### Tier List de Modelos (Referencia)

**Cerebro (High Logic)**
1. `groq/llama-3.3-70b-versatile`
2. `groq/qwen/qwen3-32b`
3. `groq/meta-llama/llama-4-maverick-17b-instruct` (Experimental)

**Secretario / Actores (High Speed)**
1. `groq/llama-3.1-8b-instant`
2. `groq/meta-llama/llama-4-scout-17b-instruct`
3. `groq/moonshotai/kimi-k2-instruct`

---
*Documento de Diseño Técnico v2.1*