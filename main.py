from scripts import historical_data
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
   logger.info(f"Ejecutando script...")
   historical_data()
   
   return None

if __name__ == "__main__":
    main()