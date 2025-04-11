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
    print("\n")
    print("*"*70)
    print("**                   OBTENCIÓN DE DATOS DE LA AEMET                 **")
    print("*"*70)
    print("\n*********************** MENÚ DE LA APLICACIÓN ************************")
    print("\n** 1. Obtener códigos de las estaciones                             **")
    print("** 2. Obtener los datos históricos                                  **")
    print("** 3. Crear archivos 'csv' históricos                               **")
    print("** 4. Previsión próximos 7 dias (todos los municipios)              **")
    print("** 5. Crear archivos 'csv' de predicción                            **")
    print("** 0. Terminar la ejecución                                         **\n")
    print("*"*70)

    selection = input("Selecciona una opción: \n").upper()
    
    match selection:

        case "1":
            print("**************** 1. Obtener códigos de las estaciones ****************\n")
            logger.info("Obteniendo códigos de estaciones EMA...")
            obtain_and_group_stations_codes()
                    
        case "2":
            print("****************** 2. Obtener los datos históricos *******************\n")
            print("** 1. Generar archivo desde cero                                    **")
            print("** 2. Reanudar la obtención de la información                       **")
            print("** 3. Recuperar información histórica desde los errores             **")
            print("** 0. Volver                                                        **")
            print("*"*70)

            subseleccion = input("Selecciona una opción: \n").upper()
            match subseleccion:
                case "1":
                    print("** 1. Generar archivo desde cero                                    **\n")
                    fecha = input("Introduce la fecha final (YYYY-MM-DD): ")
                    is_valid, message = date_validation(fecha)
                    
                    if is_valid:
                        logger.info("📝 Obteniendo la información desde cero...")
                        historical_data(fecha)
                    else:
                        logger.error(message)

                case "2":
                    print("** 2. Reanudar la obtención de la información                       **\n")
                    fecha = input("Introduce la fecha final (YYYY-MM-DD) Igual que la anterior: ")
                    is_valid, message = date_validation(fecha)
                    
                    if is_valid:
                            logger.info("Verificando grupos de estaciones pendientes...")
                            result = check_missing_group_codes()
                            if result:
                                print(f"Se han encontrado {len(result)} grupos de estaciones pendientes")
                                logger.info("📝 Reanudando desde pending_group_codes...")
                                historical_data(fecha, resume=True)
                            else:
                                logger.warning("No se encontraron grupos de estaciones pendientes o hubo un error")

                    else:  
                        logger.error(message)

                case "3":
                    print("** 3. Recuperar información histórica desde los errores             **\n")
                    logger.info("Obteniendo información desde errors.json...")
                    data_from_error_journal()

                case "0":
                    continue

                case _:
                    print("Opción no válida")
                    
        case "3":
            print("***************** 3. Crear archivos 'csv' históricos *****************")
            print("** 1. Crear temperatura_historico.csv                               **")
            print("** 2. Crear humedad_relativa_historico.csv                          **")
            print("** 3. Crear precipitaciones_historico.csv                           **")
            print("** 4. Crear viento_historico.csv                                    **")
            print("** 0. Volver                                                        **")
            print("*"*70)

            subseleccion = input("Selecciona una opción: \n").upper()
            match subseleccion:

                case "1":
                    logger.info("📝 Creando temperatura_historico.csv...")
                    historical_data_to_csv('temperatura')

                case "2":
                    logger.info("📝 Creando humedad_relativa_historico.csv...")
                    historical_data_to_csv('humedad_relativa')

                case "3":
                    logger.info("📝 Creando precipitaciones_historico.csv...")
                    historical_data_to_csv('precipitaciones')

                case "4":
                    logger.info("📝 Creando viento_historico.csv...")
                    historical_data_to_csv('viento')

                case "0":
                    continue

                case _:
                    print("Opción no válida")
        
        case "4":
            print("******** 4. Previsión próximos 7 dias (todos los municipios) *********")
            print("** 1. Obtener previsión de los próximos 7 dias                      **")
            print("** 2. Reanudar obtención de previsión de los próximos 7 dias        **")
            print("** 0. Volver                                                        **")
            print("*"*70)

            subseleccion = input("Selecciona una opción: \n").upper()
            match subseleccion:

                case "1":
                    print("** 1. Obtener previsión de los próximos 7 dias                      **")
                    logger.info("Obteniendo información...")
                    prediction_data_by_town()

                case "2":
                    print("** 2. Reanudar obtención de previsión de los próximos 7 dias        **")
                    logger.info("Verificando ciudades pendientes...")
                    result = check_missing_town_codes()
                    if result:
                        logger.info(f"Se han encontrado {len(result)} ciudades pendientes")
                        logger.info("Reanudando la obteniendo información...")
                        prediction_data_by_town(resume=True)
                    else:
                        logger.warning("No se encontraron ciudades pendientes o hubo un error")
                    
                case "0":
                    continue

                case _:
                    print("Opción no válida")
        
        case "5":            
            print("************** 5. Crear archivos 'csv' de predicción *****************")
            print("** 1. Crear prediccion_precipitaciones.csv                          **")
            print("** 2. Crear prediccion_cota_nieve.csv                               **")
            print("** 3. Crear prediccion_estado_cielo.csv                             **")
            print("** 4. Crear prediccion_viento.csv                                   **")
            print("** 5. Crear prediccion_racha_max.csv                                **")
            print("** 6. Crear prediccion_temperatura.csv                              **")
            print("** 7. Crear prediccion_sens_termica.csv                             **")
            print("** 8. Crear prediccion_humedad_relativa.csv                         **")
            print("** 0. Volver                                                        **")
            print("*"*70)

            subseleccion = input("Selecciona una opción: \n").upper()
            match subseleccion:
                case "1":
                    logger.info("📝 Creando prediccion_precipitaciones.csv...")
                    predictions_to_csv('precipitaciones')
                case "2":
                    logger.info("📝 Creando prediccion_cota_nieve.csv...")
                    predictions_to_csv('cota_nieve')
                case "3":
                    logger.info("📝 Creando prediccion_estado_cielo.csv...")
                    predictions_to_csv('estado_cielo')
                case "4":
                    logger.info("📝 Creando prediccion_viento.csv...")
                    predictions_to_csv('viento')
                case "5":
                    logger.info("📝 Creando prediccion_racha_max.csv...")
                    predictions_to_csv('racha_max')
                case "6":
                    logger.info("📝 Creando prediccion_temperatura.csv...")
                    predictions_to_csv('temperatura')
                case "7":
                    logger.info("📝 Creando prediccion_sens_termica.csv...")
                    predictions_to_csv('sens_termica')
                case "8":
                    logger.info("📝 Creando prediccion_humedad_relativa.csv...")
                    predictions_to_csv('humedad_relativa')
                case "0":
                    continue
                case _:
                    print("Opción no válida")

        case "0":
            break
        
        case _:
            logger.warning("Opción no válida")
      
   return None

if __name__ == "__main__":
    main()