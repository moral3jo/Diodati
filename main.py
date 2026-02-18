import asyncio
import logging
import os
from dotenv import load_dotenv
from app.engine import SimulationEngine
from app.ai_config import AI_CONFIG

# ... [logging config] ...

# Cargar variables de entorno
load_dotenv()

# Configuración LiteLLM (Silenciar logs)
import litellm
litellm.set_verbose = False
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

# Configuración
WORLD_CONFIG = "world_init.json"

async def main():
    print("Inicializando Project Sandbox MVP (Con LLM Arbitrator Multi-Modelo)...")
    
    # Verificar API Keys
    if not os.getenv("GROQ_API_KEY"):
        print("ADVERTENCIA: GROQ_API_KEY faltante. Los modelos de Groq fallarán.")
    if not os.getenv("GEMINI_API_KEY"):
        print("ADVERTENCIA: GEMINI_API_KEY faltante. Los modelos de Gemini fallarán.")

    print(f"Configuración IA Loaded:")
    print(f"- Cerebro: {AI_CONFIG['arbitrator_reasoning']}")
    print(f"- Formato: {AI_CONFIG['arbitrator_formatting']}")

    # Inicializar motor con Árbitro LLM y Config
    engine = SimulationEngine(arbitrator_type="llm", ai_config=AI_CONFIG)
    
    # Initialize simulation from config
    sim_id = engine.initialize_simulation(WORLD_CONFIG)
    print(f"ID de Simulación: {sim_id}")
    
    # Run 5 turns
    print("Ejecutando 5 turnos...")
    await engine.run_steps(5)
    
    print("Simulación completada. Revisa 'simulation.db' para ver los resultados.")

if __name__ == "__main__":
    asyncio.run(main())
