import json
import os
from datetime import datetime, timezone
from collections import defaultdict
from .utils import *
from .verify_files import *
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

def historical_data(final_date, resume=False):
    '''Obtiene la información histórica de las estaciones de meteorología de la AEMET - España'''
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        output_file_path = os.path.join(api_dir, 'json', 'weather_data.json')
        now = datetime.now(timezone.utc).isoformat()

        # 2. Cargar datos existentes
        if os.path.exists(output_file_path):
            with open(output_file_path, 'r', encoding='utf-8') as f:
                existing_data = json.load(f)
            
            if resume:
                # En modo resume, usamos los datos existentes
                stations_data = existing_data
                # Reconstruir processed_dates desde los datos existentes
                processed_dates = defaultdict(set)
                for station_code, station_info in existing_data.items():
                    processed_dates[station_code].update(station_info['date'].keys())
            else:
                # Si no es resume, empezamos de cero
                stations_data = {}
                processed_dates = defaultdict(set)
        else:
            stations_data = {}
            processed_dates = defaultdict(set)

        # 3. Leer los códigos de las estaciones desde JSON
        logger.info("Obteniendo códigos de estaciones EMA")
        group_codes_path = os.path.join(api_dir, 'json', 'pending_group_codes.json' if resume else 'codes_group.json')
        ema_codes = verify_json_docs(json_path_dir=group_codes_path, 
                                message="Debes crear primero el archivo de códigos EMA o pendientes")
        
        if not ema_codes:
            logger.warning("No hay códigos de estaciones para procesar")
            return None

        # 4. Configurar rango de fechas
        encoded_init_date = DEFAULT_START_DATE.replace(':', '%3A')
        end_date_str = final_date + 'T00:00:00UTC'
        encoded_end_date = end_date_str.replace(':', '%3A')

        # 5. Procesar estaciones
        total_stations = len(ema_codes)
        processed_count = 0
        updated_stations = set()

        for i, (group, stations_codes) in enumerate(ema_codes.items(), 1):
            encoded_stations_codes = stations_codes.replace(',', '%2C')
            station_codes_list = stations_codes.split(',')
            
            # En modo resume, saltar si todas las estaciones del grupo ya están completas
            if resume and all(code in processed_dates and len(processed_dates[code]) > 0 
                           for code in station_codes_list):
                logger.info(f"↩️ [{i}/{total_stations}] Grupo {group} ya procesado. Saltando...")
                continue

            logger.info(f"[{i}/{total_stations}] Procesando estaciones del {group}")

            # Obtener datos de la estación
            result = fetch_historical_station_data(
                encoded_init_date,
                encoded_end_date,
                encoded_stations_codes,
                last_request_time=now
            )

            if not result:
                logger.warning(f"No se obtuvieron datos para el {group}")
                continue

            # Procesar cada estación en el resultado
            logger.info(f"Procesando grupo: [{group}]")
            for station_data in result:
                current_station_code = station_data.get('town_code')

                # Filtrar solo las fechas que no hemos procesado
                new_data = {}
                for date, values in station_data['date'].items():
                    if date not in processed_dates.get(current_station_code, set()):
                        new_data[date] = {
                            'values': values,
                            'ts_insert': now if current_station_code not in stations_data else stations_data[current_station_code]['date'].get(date, {}).get('ts_insert', now),
                            'ts_update': now
                        }

                if not new_data and resume:
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
                processed_dates[current_station_code].update(new_data.keys())
                processed_count += len(new_data)
                updated_stations.add(current_station_code)

            # Guardar progreso después de cada grupo (directamente en weather_data.json)
            if updated_stations:
                with open(output_file_path, 'w', encoding='utf-8') as f:
                    json.dump(stations_data, f, ensure_ascii=False, indent=4)
                logger.info(f"Progreso guardado después del grupo {group}")
                updated_stations.clear()

            time.sleep(REQUEST_DELAY)

        logger.info(f"✅ Proceso completado. Datos nuevos procesados: {processed_count}")
        return stations_data
        
    except KeyError as e:
        logger.error(f"❌Error de key {str(e)}")
    except ValueError as e:
        logger.error(f"❌Error al acceder al JSON: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"❌Error al procesar archivos JSON: {str(e)}")
    except Exception as e:
        logger.error(f"❌Error inesperado: {str(e)}", exc_info=True)

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
            logger.error(f"❌No se obtuvieron datos válidos")
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
        logger.error(f"❌Error de key {str(e)}")
    except ValueError as e:
        logger.error(f"❌Error al acceder al JSON: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"❌Error al procesar archivos JSON: {str(e)}")
    except Exception as e:
        logger.error(f"❌Error inesperado data_from_error_journal: {str(e)}", exc_info=True)

def prediction_data_by_town(resume=False, recovery=False):
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

def prediction_data_from_error_journal():
    '''Función para actualizar prediction_data.json con la información desde error_prediction.json'''
    try:
        # 1. Configuración inicial
        script_dir = os.path.dirname(os.path.abspath(__file__))
        api_dir = os.path.dirname(script_dir)
        prediction_data_path = os.path.join(api_dir, 'json', 'prediction_data.json')
        error_journal_path = os.path.join(api_dir, 'error_journal', 'error_prediction.json')
        now = datetime.now(timezone.utc).isoformat()
        
        # Verificar que existe error_prediction.json
        if not os.path.exists(error_journal_path):
            logger.warning(f"❗No existe el archivo error_prediction.json")
            return None
        
        
        # 2. Usar verify_json_docs para cargar los archivos JSON
        prediction_data = verify_json_docs(prediction_data_path, [])
        error_entries = verify_json_docs(error_journal_path, [])
        
        # Convertir a diccionario para acceso eficiente
        prediction_dict = {str(town.get('id')): town for town in prediction_data if 'id' in town}
        
        if not error_entries:
            logger.warning(f"❗El archivo error_prediction.json está vacío")
            return None
        
        logger.info(f"Procesando {len(error_entries)} entradas del journal de errores")
        
        # 3. Procesar cada entrada del journal de errores
        processed_count = 0
        
        for entry in error_entries:
            town_code = entry.get('station_code')
            if not town_code:
                logger.warning(f"❗Entrada sin código de municipio: {entry}")
                continue
            
            # Obtener nuevos datos para este municipio
            town_data = fetch_prediction_station_data(town_code, last_request_time=now)
            
            if town_data:
                town_id = str(town_data.get('id', town_code))
                # Conservar timestamp de inserción si existe
                town_data['ts_insert'] = prediction_dict.get(town_id, {}).get('ts_insert', now)
                town_data['ts_update'] = now
                
                # Actualizar el diccionario
                prediction_dict[town_id] = town_data
                processed_count += 1
                logger.info(f"Datos actualizados para el municipio {town_id}")
                
                # Guardar progreso incremental
                with open(prediction_data_path, 'w', encoding='utf-8') as f:
                    json.dump(list(prediction_dict.values()), f, ensure_ascii=False, indent=4)
            else:
                logger.warning(f"❗No se pudieron recuperar datos para el municipio {town_code}")
            
            # Pausar entre peticiones
            time.sleep(REQUEST_DELAY)
        
        # 4. Limpiar el journal de errores si se procesaron correctamente
        if processed_count > 0:
            with open(error_journal_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)
            logger.info(f"Journal de errores limpiado correctamente")
        
        logger.info(f"Proceso completado. Municipios actualizados: {processed_count}")
        return list(prediction_dict.values())
        
    except KeyError as e:
        logger.error(f"❌Error de clave: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"❌Error al acceder al JSON: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"❌Error al procesar archivos JSON: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"❌Error inesperado en prediction_data_from_error_journal: {str(e)}", exc_info=True)
        return None
