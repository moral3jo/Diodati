```python
import asyncio
import logging
import os
from dotenv import load_dotenv
from app.engine import SimulationEngine

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Cargar variables de entorno
load_dotenv()

# Configuración
WORLD_CONFIG = "world_init.json"

def main():
    print("Inicializando Project Sandbox MVP (Con LLM Arbitrator)...")
    
    # Verificar API Key
    if not os.getenv("GEMINI_API_KEY"):
        print("ADVERTENCIA: GEMINI_API_KEY no encontrada en variables de entorno.")
    
    # Inicializar motor con Árbitro LLM
    engine = SimulationEngine(arbitrator_type="llm")
    
    # Initialize simulation from config
    sim_id = engine.initialize_simulation(WORLD_CONFIG)
    print(f"ID de Simulación: {sim_id}")
    
    # Run 5 turns
    print("Ejecutando 5 turnos...")
    await engine.run_steps(5)
    
    print("Simulación completada. Revisa 'simulation.db' para ver los resultados.")

if __name__ == "__main__":
    asyncio.run(main())
