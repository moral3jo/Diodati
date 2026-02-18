# Configuración de Modelos de IA
# Define aquí qué modelo se usa para cada rol específico.

AI_CONFIG = {
    # Cerebro del Árbitro: Encargado de la lógica compleja, física y resolución de conflictos.
    # Requiere un modelo potente (High Intelligence).
    "arbitrator_reasoning": "groq/llama-3.3-70b-versatile",

    # Formateador del Árbitro: Encargado de convertir el texto a JSON estricto.
    # Requiere un modelo rápido y obediente con esquemas (High Speed/Compliance).
    # "groq/llama-3.1-8b-instant" o modelos Qwen si están disponibles.
    "arbitrator_formatting": "groq/llama-3.1-8b-instant",

    # Agentes (NPCs): Modelos para los personajes controlados por IA.
    # Deben ser rápidos y capaces de rolear.
    "agent_default": "groq/llama-3.1-8b-instant"
}
