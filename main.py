from scripts import historical_data, obtain_stations_EMA_code, data_to_csv, date_validation
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)



# Main de la aplicación
def main():
   
   while True:
    print("\n*** MENÚ DE LA APLICACIÓN ***")
    print("1. Obtener códigos de las estaciones")
    print("2. Obtener los datos históricos")
    print("3. Crear temperature.csv")
    print("4. Crear precipitation.csv")
    print("5. Crear hrMedia.csv")
    print("6. Terminar la ejecución")
    
    selection = input("Selecciona una opción: ").upper()
    
    match selection:
        case "1":
            # Obtener códigos de estaciones
            logger.info("Obteniendo códigos de estaciones EMA...")
            obtain_stations_EMA_code()
            logger.info("¡Códigos de estaciones EMA obtenidos!")
                    
        case "2":
            # Obtener toda la información solicitada de las estaciones en el rango de fecha
            fecha = input("Introduce la fecha final (YYYY-MM-DD): ")
            is_valid, message = date_validation(fecha)
            
            if is_valid:
                historical_data(fecha)
            logger.error(message)
                    
        case "3":
            # Crea un archivo con los datos de las temperatura en /csv/temperature.csv
            logger.info("Creando temperature.csv...")
            data_to_csv('temperature')
                    
        case "4":
            # Crea un archivo con los datos de las precipitaciones en /csv/precipitation.csv
            logger.info("Creando precipitation.csv...")
            data_to_csv('precipitation')
        
        case "5":
            # Crea un archivo con los datos de las racha media en /csv/hrMedia.csv
            logger.info("Creando hrMedia.csv...")
            data_to_csv('hrMedia')

        case "6":
            break
        
        case _:
            print("Opción no válida")
      
   return None

if __name__ == "__main__":
    main()