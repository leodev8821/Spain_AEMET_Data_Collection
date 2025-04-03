from datetime import datetime
import re
from scripts import historical_data, obtain_stations_EMA_code, temp_to_csv
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def date_validation(date_str):
    try:
        # Verificar formato básico con regex
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            return False, "Formato inválido. Debe ser YYYY-MM-DD"
        
        # Validar que sea una fecha válida
        datetime.strptime(date_str, "%Y-%m-%d")
        return True, ""
    
    except ValueError:
        return False, "Fecha inválida. Por favor, ingrese una fecha correcta."

def main():
   
   while True:
    print("\n*** MENÚ DE LA APLICACIÓN ***")
    print("1. Obtener códigos de las estaciones")
    print("2. Obtener los datos históricos")
    print("3. Crear temperatura.csv")
    print("4. Crear precipitaciones.csv")
    print("5. Crear racha.csv")
    print("6. Terminar la ejecución")
    
    selection = input("Selecciona una opción: ").upper()
    
    match selection:
        case "1":
            # Obtener códigos de estaciones
            logger.info("Obteniendo códigos de estaciones EMA...")
            obtain_stations_EMA_code()
            logger.info("¡Códigos de estaciones EMA obtenidos!")
                    
        case "2":
            fecha = input("Introduce la fecha final (YYYY-MM-DD): ")
            is_valid, message = date_validation(fecha)
            
            if is_valid:
                historical_data(fecha)
            logger.error(message)
                    
        case "3":
            logger.info("Creando temperature.csv...")
            temp_to_csv()
                    
        case "4":
            logger.info("Creando precipitaciones.csv...")
            temp_to_csv()
        
        case "5":
            logger.info("Creando racha.csv...")
            temp_to_csv()

        case "6":
            break
        
        case _:
            print("Opción no válida")
      
   return None

if __name__ == "__main__":
    main()