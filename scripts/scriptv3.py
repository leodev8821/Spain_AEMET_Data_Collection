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

def historical_data(final_date):
    '''Obtiene la información histórica de las estaciones de meteorología de la AEMET - España'''
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

            # Obtener datos de la estación (solo fechas faltantes)
            result = fetch_historical_station_data(
                encoded_init_date,
                encoded_end_date,
                encoded_stations_codes,
                last_request_time=now
            )

            # Si no hay información de esa estación, continúa con la siguiente
            if not result:
                logger.warning(f"No se obtuvieron datos para el {group}")
                continue

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
            processed_dates[current_station_code].update(new_dates_for_group)

            # Guardar progreso cada grupo de estaciones o al final
            if i % 1 == 0 or i == total_stations:
                logger.info(f"[{i}] grupo de estaciones guardado en progress")
                save_progress(progress_file_path, processed_dates, stations_data)

            # Una espera para la nueva fetch
            time.sleep(REQUEST_DELAY)

        # 6. Guardar resultados finales
        if stations_data:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(stations_data, f, ensure_ascii=False, indent=4)
            os.remove(progress_file_path)
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

def data_from_error_journal():
    '''Función para actualizar el weather_data.json con la información desde errors.json'''
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        weather_data_path = os.path.join(api_dir, 'json', 'weather_data.json')
        
        # Cargar el JSON principal
        weather_data = verify_json_docs(weather_data_path, message="No esta creado weather_data.json")
        now = datetime.now(timezone.utc).isoformat()

        # Obtener datos del journal de errores
        result = fetch_error_data(last_request_time=now)
        
        if not result:
            logger.error("No se obtuvieron datos válidos")
            raise ValueError("No se obtuvieron datos válidos")

        new_dates_for_group = set()

        # Procesar cada entrada del journal de errores
        for entry in result:
            town_code = entry.get("town_code")
            if not town_code:
                continue
                
            # Obtener las fechas/datos del entry actual
            date_data = entry.get("date", {})
            if not date_data:
                continue
                
            # Si el town_code no existe en weather_data, crearlo
            if town_code not in weather_data:
                weather_data[town_code] = {
                    "town_code": town_code,
                    "province": entry.get("province", ""),
                    "town": entry.get("town", ""),
                    "date": {}
                }
                
            # Para cada fecha en el entry actual
            for date_str, values in date_data.items():
                # Si la fecha ya existe, actualizamos los valores
                # Si no existe, la añadimos
                weather_data[town_code]["date"][date_str] = {
                    "values": values,
                    "ts_insert": now,
                    "ts_update": now
                }
                new_dates_for_group.add(date_str)

        # Guardar los cambios en el archivo weather_data.json
        with open(weather_data_path, 'w', encoding='utf-8') as f:
            json.dump(weather_data, f, ensure_ascii=False, indent=4)

        logger.info(f"Datos actualizados correctamente. Nuevas fechas añadidas: {new_dates_for_group}")
        
    except KeyError as e:
        logger.error(f"Error de key {str(e)}")
    except ValueError as e:
        logger.error(f"Error al acceder al JSON: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"Error al procesar archivos JSON: {str(e)}")
    except Exception as e:
        logger.error(f"Error inesperado data_from_error_journal: {str(e)}", exc_info=True)

def prediction_data_by_town(resume=False):
    '''Obtiene las predicciones meteorologicas de la AEMET - España por cada municipio'''
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        
        prediction_data_file_path = os.path.join(api_dir, 'json', 'prediction_data.json')
        now = datetime.now(timezone.utc).isoformat()

        # 2. Cargar datos existentes si el archivo existe
        if os.path.exists(prediction_data_file_path):
            with open(prediction_data_file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            # Convertir a diccionario con id como clave para fácil acceso
            existing_data_dict = {str(town['id']): town for town in existing_data}
        else:
            existing_data_dict = {}

        # 3. Determinar el conjunto de municipios a procesar
        town_codes_path = os.path.join(api_dir, 'json', 'pending_towns_codes.json' if resume else 'towns_codes.json')
        
        towns_codes = verify_json_docs(
            json_path_dir=town_codes_path,
            message="❗ No existen códigos pendientes" if resume else "Debes crear primero el archivo de códigos"
        )

        if not towns_codes:
            logger.warning("❗ No hay municipios para procesar")
            return

        # 4. Procesar municipios
        total_towns = len(towns_codes)
        processed_count  = 0

        for i, (code, name) in enumerate(towns_codes.items(), 1):
            town_id = str(code)
            
            # En modo resume, saltar si ya existe
            if resume and town_id in existing_data_dict:
                logger.info(f"↩️ [{i}/{total_towns}] Municipio {name} ya existe. Saltando...")
                continue

            logger.info(f"🌐 [{i}/{total_towns}] Procesando el municipio {name}")

            # Obtener datos del municipio
            town_data = fetch_prediction_station_data(code, last_request_time=now)

            if not town_data:
                logger.warning(f"❗ No se obtuvieron datos para el municipio {code}")
                continue

            if town_data:
                # Mantener timestamp original o crear uno nuevo
                town_data['ts_insert'] = existing_data_dict.get(town_id, {}).get('ts_insert', now)
                town_data['ts_update'] = now
                existing_data_dict[town_id] = town_data
                processed_count += 1

                # Guardar progreso después de cada municipio
                with open(prediction_data_file_path, 'w', encoding='utf-8') as f:
                    json.dump(list(existing_data_dict.values()), f, ensure_ascii=False, indent=4)
            else:
                logger.warning(f"❗ No se obtuvieron datos para {name}")

            time.sleep(REQUEST_DELAY)

        logger.info(f"✅ Proceso completado. Municipios procesados: {processed_count}/{total_towns}")
        return list(existing_data_dict.values())
        
    except KeyError as e:
        logger.error(f"❌ Error de clave: {str(e)}")
    except (ValueError, json.JSONDecodeError) as e:
        logger.error(f"❌ Error al procesar JSON: {str(e)}")
    except Exception as e:
        logger.error(f"❌ Error inesperado: {str(e)}", exc_info=True)