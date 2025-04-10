from scripts import *
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
    print("\n********************* MENÚ DE LA APLICACIÓN ************************")
    print("1. Obtener códigos de las estaciones")
    print("2. Obtener los datos históricos")
    print("3. Crear archivos 'csv' históricos")
    print("4. Recuperar información histórica a los errores")
    print("5. Obtener previsión de los próximos 7 dias de todos los municipios")
    print("6. Crear archivos 'csv' de previsión")
    print("8. Generar pending_towns_codes.json")
    print("0. Terminar la ejecución")
    print("\n********************************************************************")

    selection = input("Selecciona una opción: ").upper()
    
    match selection:
        case "1":
            # Obtener códigos de estaciones
            print("********************* 1. Obtener códigos de las estaciones *********************")
            logger.info("Obteniendo códigos de estaciones EMA...")
            obtain_and_group_stations_codes()
                    
        case "2":
            # Obtener toda la información solicitada de las estaciones en el rango de fecha
            print("********************* 2. Obtener los datos históricos *********************")
            fecha = input("Introduce la fecha final (YYYY-MM-DD): ")
            is_valid, message = date_validation(fecha)
            
            if is_valid:
                historical_data(fecha)
            logger.error(message)
                    
        case "3":
            # Crea el archivo csv histórico
            print("********************* 3. Crear archivos 'csv' históricos *********************")
            print("1. Crear temperatura_historico.csv")
            print("2. Crear humedad_relativa_historico.csv")
            print("3. Crear precipitaciones_historico.csv")
            print("4. Crear viento_historico.csv")
            print("5. Volver")

            subseleccion = input("Selecciona una opción: ").upper()
            match subseleccion:
                case "1":
                    logger.info("Creando temperatura_historico.csv...")
                    historical_data_to_csv('temperatura')
                case "2":
                    logger.info("Creando humedad_relativa_historico.csv...")
                    historical_data_to_csv('humedad_relativa')
                case "3":
                    logger.info("Creando precipitaciones_historico.csv...")
                    historical_data_to_csv('precipitaciones')
                case "4":
                    logger.info("Creando viento_historico.csv...")
                    historical_data_to_csv('viento')
                case "5":
                    continue
                case _:
                    print("Opción no válida")
        
        case "4":
            # Recuperar datos de estaciones con errores
            print("********************* 4. Recuperar información histórica de los errores *********************")
            logger.info("Obteniendo información desde errors.json...")
            data_from_error_journal()
        
        case "5":
            # Crea un archivo con los datos de las racha media en /csv/humedad_relativa.csv
            print("********************* 5. Obtener previsión de los próximos 7 dias de todos los municipios *********************")
            logger.info("Obteniendo información...")
            prediction_data_by_town()
        
        case "6":            
            # Crea el archivo csv de prediccion
            print("********************* 3. Crear archivos 'csv' históricos *********************")
            print("1. Crear prediccion_precipitaciones.csv")
            print("2. Crear prediccion_cota_nieve.csv")
            print("3. Crear prediccion_estado_cielo.csv")
            print("4. Crear prediccion_viento.csv")
            print("5. Crear prediccion_racha_max.csv")
            print("6. Crear prediccion_temperatura.csv")
            print("7. Crear prediccion_sens_termica.csv")
            print("8. Crear prediccion_humedad_relativa.csv")
            print("0. Volver")

            subseleccion = input("Selecciona una opción: ").upper()
            match subseleccion:
                case "1":
                    logger.info("Creando prediccion_precipitaciones.csv...")
                    predictions_to_csv('precipitaciones')
                case "2":
                    logger.info("Creando prediccion_cota_nieve.csv...")
                    predictions_to_csv('cota_nieve')
                case "3":
                    logger.info("Creando prediccion_estado_cielo.csv...")
                    predictions_to_csv('estado_cielo')
                case "4":
                    logger.info("Creando prediccion_viento.csv...")
                    predictions_to_csv('viento')
                case "5":
                    logger.info("Creando prediccion_racha_max.csv...")
                    predictions_to_csv('racha_max')
                case "6":
                    logger.info("Creando prediccion_temperatura.csv...")
                    #predictions_to_csv('temperatura')
                case "7":
                    logger.info("Creando prediccion_sens_termica.csv...")
                    #predictions_to_csv('sens_termica')
                case "8":
                    logger.info("Creando prediccion_humedad_relativa.csv...")
                    #predictions_to_csv('humedad_relativa')
                case "0":
                    continue
                case _:
                    print("Opción no válida")

        case "8":
            # Verificar ciudades faltantes
            print("********************* 8. Generar pending_towns_codes.json *********************")
            logger.info("Verificando ciudades pendientes...")
            try:
                result = check_missing_town_codes()
                if result:
                    logger.info(f"Se han encontrado {len(result)} ciudades pendientes")
                else:
                    logger.warning("No se encontraron ciudades pendientes o hubo un error")
            except Exception as e:
                logger.error(f"Error al ejecutar check_missing_town_codes: {e}")

        case "0":
            break
        
        case _:
            logger.warning("Opción no válida")
      
   return None

if __name__ == "__main__":
    main()