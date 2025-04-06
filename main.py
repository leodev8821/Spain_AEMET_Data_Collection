from scripts import historical_data, obtain_stations_EMA_code, data_to_csv, date_validation, group_codes
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)



# Main de la aplicación
def main():
   
   while True:
    print("\n*** MENÚ DE LA APLICACIÓN ***")
    print("1. Obtener códigos de las estaciones")
    print("2. Obtener los datos históricos")
    print("3. Crear temperatura.csv")
    print("4. Crear precipitaciones.csv")
    print("5. Crear viento.csv")
    print("6. Crear humedad_relativa.csv")
    print("7. Agrupar codigos en 25")
    print("8. Terminar la ejecución")
    
    selection = input("Selecciona una opción: ").upper()
    
    match selection:
        case "1":
            # Obtener códigos de estaciones
            logger.info("Obteniendo códigos de estaciones EMA...")
            obtain_stations_EMA_code()
                    
        case "2":
            # Obtener toda la información solicitada de las estaciones en el rango de fecha
            fecha = input("Introduce la fecha final (YYYY-MM-DD): ")
            is_valid, message = date_validation(fecha)
            
            if is_valid:
                historical_data(fecha)
            logger.error(message)
                    
        case "3":
            # Crea un archivo con los datos de las temperatura en /csv/temperatura.csv
            logger.info("Creando temperatura.csv...")
            data_to_csv('temperatura')
                    
        case "4":
            # Crea un archivo con los datos de las precipitaciones en /csv/precipitaciones.csv
            logger.info("Creando precipitaciones.csv...")
            data_to_csv('precipitaciones')
        
        case "5":
            # Crea un archivo con los datos de las racha media en /csv/viento.csv
            logger.info("Creando viento.csv...")
            data_to_csv('viento')
        
        case "6":
            # Crea un archivo con los datos de las racha media en /csv/humedad_relativa.csv
            logger.info("Creando humedad_relativa.csv...")
            data_to_csv('humedad_relativa')
        
        case "7":
            # Crea un archivo con los datos de las racha media en /csv/humedad_relativa.csv
            logger.info("Agrupando codigos EMA...")
            group_codes()

        case "8":
            break
        
        case _:
            logger.warning("Opción no válida")
      
   return None

if __name__ == "__main__":
    main()