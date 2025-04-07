import json
import os
from datetime import datetime, timezone
from collections import defaultdict
from .utils import *
from .fetch_station_data import *
import logging
import time

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s --> %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración global
DEFAULT_START_DATE = '2025-01-01T00:00:00UTC'
REQUEST_DELAY = 3.0  # segundos entre solicitudes

# Obtiene la información histórica de las estaciones de meteorología de la AEMET - España
def historical_data(final_date):
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        
        progress_file_path = os.path.join(api_dir, 'json', 'progress.json')
        output_file_path = os.path.join(api_dir, 'json', 'weather_data.json')
        now = datetime.now(timezone.utc).isoformat()

        # 2. Leer los códigos de las estaciones desde JSON
        logger.info("Obteniendo códigos de estaciones EMA")
        json_path = os.path.join(api_dir, 'json', 'codes_group.json')
        ema_codes = verify_json_docs(json_path_dir=json_path, message="Debes crear primero el archivo de códigos EMA - Opción 1")
        
        # 3. Cargar progreso previo
        processed_dates, stations_data = load_progress(progress_file_path)

        # 4. Configurar rango de fechas
        encoded_init_date = DEFAULT_START_DATE.replace(':', '%3A')
        end_date_str = final_date + 'T00:00:00UTC'
        encoded_end_date = end_date_str.replace(':', '%3A')

        # 5. Procesar estaciones
        total_stations = len(ema_codes)

        for i, (group, stations_codes) in enumerate(ema_codes.items(), 1):
            encoded_stations_codes = stations_codes.replace(',', '%2C')
            logger.info(f"[{i}/{total_stations}] Procesando estaciónes del {group}")

            if stations_codes not in processed_dates:
                processed_dates[stations_codes] = set()

            # Determinar fechas faltantes para esta estación
            #existing_dates = processed_dates.get(stations_codes, set())

            # Obtener datos de la estación (solo fechas faltantes)
            result = fetch_station_data(
                encoded_init_date,
                encoded_end_date,
                encoded_stations_codes,
                last_request_time=now
            )

            # Si no hay información de esa estación, continúa con la siguiente
            if not result:
                logger.warning(f"No se obtuvieron datos para el {group}")
                continue

            # Asegurarnos de que la estación existe en processed_dates
            # if stations_codes not in processed_dates:
            #     processed_dates[stations_codes] = set()

            # Iterar sobre cada estación en result
            new_dates_for_group  = set()
            for station_data in result: 
                current_station_code = station_data.get('town_code')
                logger.info(f"Procesando estación: [{current_station_code}]")

                # Filtrar solo las fechas que no hemos procesado
                new_data = {}
                for date, values in station_data['date'].items():
                    if date not in processed_dates[stations_codes]:
                        new_data[date] = {
                            'values': values,
                            'ts_insert': now,
                            'ts_update': now
                        }

                        new_dates_for_group.add(date)

                # Si no hay información nueva para la estación, sigue con la siguiente
                if not new_data:
                    logger.info(f"No hay datos nuevos para {current_station_code}")
                    continue

                # Obtener el código de la estación actual (puede variar si hay múltiples)
                #current_station_code = station_data['town_code']

                # Actualizar los datos de la estación
                if current_station_code not in stations_data:
                    stations_data[current_station_code] = {
                        "town_code": current_station_code,
                        "province": station_data["province"],
                        "town": station_data["town"],
                        "date": {}
                    }
                
                # Agregar solo datos nuevos
                stations_data[current_station_code]['date'].update(new_data)
                
                # Actualizar fechas procesadas
                #processed_dates[current_station_code].update(new_data.keys())
            processed_dates[current_station_code].update(new_dates_for_group)

                # Actualizar timestamps para las nuevas fechas
                # for date_key in new_data.keys():
                #     update_timestamp(stations_data, current_station_code, date_key)

            # Guardar progreso cada grupo de estaciones o al final
            if i % 1 == 0 or i == total_stations:
                logger.info(f"[{i}/{total_stations}] grupo de estaciones guardado en progress")
                save_progress(progress_file_path, processed_dates, stations_data)

            # Una espera para la nueva fetch
            time.sleep(REQUEST_DELAY)

        # 6. Guardar resultados finales
        if stations_data:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(stations_data, f, ensure_ascii=False, indent=4)
            #os.remove(progress_file)
            logger.info(f"Datos guardados en {output_file_path}")
            return stations_data
        
        logger.warning("No se obtuvieron datos válidos")
        return None
        
    except KeyError as e:
        logger.error(f"Error de key {str(e)}")
    except ValueError as e:
        logger.error(f"Error al acceder al JSON: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Error al procesar archivos JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado ScriptV3: {str(e)}", exc_info=True)